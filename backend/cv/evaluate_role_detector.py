"""Offline role screening on sparse, source-pinned development labels.

Unmatched predictions are NOT false positives: frames are not fully labelled.
No runtime model selection, tracking changes or shared-schema changes here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
from time import perf_counter


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def iou(a, b):
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union > 0 else 0.0


def match(labels, predictions, *, box_iou=.5, foot_gate=35):
    """One-to-one, role-blind greedy spatial matching; never match by class."""
    candidates = []
    for g, label in enumerate(labels):
        for p, prediction in enumerate(predictions):
            box = prediction["xyxy"]
            if "xyxy" in label:
                score = iou(label["xyxy"], box)
                if score >= box_iou:
                    candidates.append((-score, g, p))
            else:
                distance = math.hypot((box[0]+box[2])/2-label["xy"][0], box[3]-label["xy"][1])
                if distance <= foot_gate:
                    candidates.append((distance, g, p))
    assigned, used = {}, set()
    for _, g, p in sorted(candidates):
        if g not in assigned and p not in used:
            assigned[g] = p
            used.add(p)
    return [{**label, "prediction": predictions[assigned[g]] if g in assigned else None} for g, label in enumerate(labels)]


def summarize(rows):
    scored = [row for row in rows if row["role"] in {"player", "goalkeeper", "referee"}]
    classes = {}
    for role in ("player", "goalkeeper", "referee"):
        subset = [row for row in scored if row["role"] == role]
        confusion = Counter(row["prediction"]["role"] if row["prediction"] else "missed" for row in subset)
        classes[role] = {"labels": len(subset), "predicted": dict(confusion),
                         "correct_fraction_of_labels": confusion[role]/len(subset) if subset else None}
    special = [row for row in scored if row["role"] != "player"]
    return {"classes": classes, "nonplayers_predicted_player": sum(bool(row["prediction"]) and row["prediction"]["role"] == "player" for row in special),
            "nonplayer_labels": len(special), "precision": None, "mAP": None,
            "note": "Sparse development labels: no full-frame precision/mAP, independent generalization or full detection recall claim."}


def checked(root, relative, expected=None):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing/outside-workspace artifact: {relative}")
    if expected is not None and digest(path) != expected:
        raise ValueError(f"Artifact hash mismatch: {relative}")
    return path


def load_samples(root, protocol):
    samples = []
    for dataset in protocol["datasets"]:
        fixture = checked(root, dataset["fixture"], dataset["fixture_sha256"])
        data = json.loads(fixture.read_text(encoding="utf-8"))
        if dataset["format"] == "context_boxes":
            labels = data["labels"]
            clips = [{"source": dataset["source"], "source_sha256": data["source_sha256"], "frames": [
                {"frame": frame, "people": [label for label in labels if label["frame"] == frame]}
                for frame in data["frames"]]}]
        else:
            clips = [{**clip, "source": dataset["sources"][clip["name"]]} for clip in data["clips"]]
        for clip in clips:
            source = checked(root, clip["source"], clip["source_sha256"])
            for frame in clip["frames"]:
                people = []
                for person in frame["people"]:
                    role = person["role"]
                    if role in {"red_outfield", "white_outfield", "white", "opponent"}:
                        role = "player"
                    people.append({**person, "role": role})
                samples.append({"source": str(source.relative_to(root)), "frame": frame["frame"], "labels": people})
    return samples


def run(root, protocol_path, output):
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    samples = load_samples(root, protocol)
    weights = [(item, checked(root, item["path"], item["sha256"])) for item in protocol["models"]]
    os.environ["YOLO_CONFIG_DIR"] = str(root / ".tmp/ultralytics")
    os.environ["YOLO_AUTOINSTALL"] = "false"
    import cv2
    import torch
    import ultralytics
    from ultralytics import YOLO
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for this protocol; do not silently benchmark CPU")
    torch.set_num_threads(4)
    output.mkdir(parents=True)
    result = {"protocol_sha256": digest(protocol_path), "torch": torch.__version__,
              "ultralytics": ultralytics.__version__, "gpu": torch.cuda.get_device_name(0),
              "runtime_changed": False, "runs": []}
    for item, path in weights:
        model = YOLO(str(path))
        names = {str(key): value for key, value in model.names.items()}
        if names != item["class_map"]:
            raise ValueError("Checkpoint class map differs from locked protocol")
        classes = [int(key) for key, value in names.items() if value in {"player", "person", "referee", "goalkeeper"}]
        for size in protocol["image_sizes"]:
            rows, predictions, timings = [], [], []
            # Warm-up outside measured frames; one decoded frame in memory at a time.
            first = samples[0]
            cap = cv2.VideoCapture(str(root / first["source"]))
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, first["frame"])
                ok, image = cap.read()
                if not ok:
                    raise ValueError("Cannot decode warm-up frame")
                model.predict(image, classes=classes, imgsz=size, conf=protocol["confidence"], device=0, verbose=False)
            finally:
                cap.release()
            torch.cuda.reset_peak_memory_stats()
            for sample in samples:
                cap = cv2.VideoCapture(str(root / sample["source"]))
                try:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, sample["frame"])
                    ok, image = cap.read()
                    if not ok:
                        raise ValueError("Cannot decode evaluation frame")
                finally:
                    cap.release()
                torch.cuda.synchronize()
                started = perf_counter()
                prediction = model.predict(image, classes=classes, imgsz=size, conf=protocol["confidence"], iou=protocol["nms_iou"], device=0, verbose=False)[0]
                torch.cuda.synchronize()
                timings.append((perf_counter()-started)*1000)
                boxes = [{"xyxy": box, "confidence": confidence, "role": "player" if names[str(int(cls))] == "person" else names[str(int(cls))]}
                         for box, confidence, cls in zip(prediction.boxes.xyxy.cpu().tolist(), prediction.boxes.conf.cpu().tolist(), prediction.boxes.cls.cpu().tolist())]
                predictions.append({"source": sample["source"], "frame": sample["frame"], "boxes": boxes})
                for gate in protocol["foot_gates_px"]:
                    matched = match(sample["labels"], boxes, box_iou=protocol["box_iou"], foot_gate=gate)
                    rows.extend({**row, "source": sample["source"], "frame": sample["frame"], "foot_gate_px": gate} for row in matched)
            groups = [{"source": source, "foot_gate_px": gate, **summarize([row for row in rows if row["source"] == source and row["foot_gate_px"] == gate])}
                      for source in sorted({sample["source"] for sample in samples}) for gate in protocol["foot_gates_px"]]
            entry = {"model": item["id"], "class_map": names, "image_size": size, "frames": len(samples), "milliseconds_per_frame": timings,
                     "mean_ms": sum(timings)/len(timings), "peak_allocated_mb": torch.cuda.max_memory_allocated()/1024**2,
                     "groups": groups, "summary_at_primary_gate": summarize([row for row in rows if row["foot_gate_px"] == protocol["primary_foot_gate_px"]])}
            stem = f'{item["id"]}-{size}'
            (output / f"{stem}-observations.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
            (output / f"{stem}-predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")
            result["runs"].append(entry)
            (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(stem, json.dumps(entry["summary_at_primary_gate"]), f'{entry["mean_ms"]:.1f}ms', flush=True)
        del model
        import gc
        gc.collect()
        torch.cuda.empty_cache()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    destination = args.output.resolve()
    if not destination.is_relative_to(workspace):
        raise ValueError("Output must stay in workspace")
    run(workspace, checked(workspace, args.protocol), destination)
