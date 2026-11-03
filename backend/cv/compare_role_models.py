"""Compare a balanced small checkpoint with its frozen baseline; never deploy."""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import gc
import json
from pathlib import Path

from backend.cv.evaluate_role_detector import checked, digest, match
from backend.cv.finetune_roles import evaluate, setup, write_json
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def frame_confusion(labels, predictions):
    """Role-blind spatial matching followed by role scoring, including extra boxes."""
    predictions = [{**prediction, "index": i} for i, prediction in enumerate(predictions)]
    matched = match(labels, predictions, box_iou=.5)
    confusion, extras, used = Counter(), Counter(), set()
    for row in matched:
        prediction = row["prediction"]
        confusion[(row["role"], prediction["role"] if prediction else "missed")] += 1
        if prediction:
            used.add(prediction["index"])
    for prediction in predictions:
        if prediction["index"] not in used:
            extras[prediction["role"]] += 1
    return confusion, extras


def operating_metrics(confusion, extras):
    result = {}
    for role in NAMES:
        tp = confusion[(role, role)]
        fn = sum(count for (truth, predicted), count in confusion.items() if truth == role and predicted != role)
        fp = extras[role] + sum(count for (truth, predicted), count in confusion.items() if predicted == role and truth != role)
        result[role] = {"tp": tp, "fp": fp, "fn": fn, "precision": tp/(tp+fp) if tp+fp else 0.,
                        "recall": tp/(tp+fn) if tp+fn else 0.}
    return {"classes": result, "player_called_referee": confusion[("player", "referee")],
            "nonplayers_called_player": sum(confusion[(role, "player")] for role in ("goalkeeper", "referee")),
            "confusion": {role: {predicted: confusion[(role, predicted)] for predicted in NAMES+["missed"]} for role in NAMES},
            "unmatched_predictions": dict(extras)}


def validation_choice(baseline, candidate, gate):
    checks = {"referee_ap50_gain": candidate["classes"]["referee"]["map50"]-baseline["classes"]["referee"]["map50"] >= gate["referee_map50_gain_min"]-1e-12,
              "overall_map_guard": candidate["map50_95"] >= baseline["map50_95"]-gate["overall_map50_95_drop_max"]-1e-12,
              "player_ap_guard": candidate["classes"]["player"]["map50"] >= baseline["classes"]["player"]["map50"]-gate["player_map50_drop_max"]-1e-12,
              "keeper_ap_guard": candidate["classes"]["goalkeeper"]["map50"] >= baseline["classes"]["goalkeeper"]["map50"]-gate["goalkeeper_map50_drop_max"]-1e-12}
    return {"checks": checks, "preferred_by_validation": "balanced" if all(checks.values()) else "baseline"}


def fixed_confidence(weights, dataset, manifest, split, confidence, image_size):
    import cv2
    from ultralytics import YOLO
    model = YOLO(str(weights))
    if list(model.names.values()) != NAMES:
        raise ValueError("Unexpected checkpoint role IDs")
    confusion, extras = Counter(), Counter()
    frames = 0
    for row in manifest["files"]:
        if row["split"] != split:
            continue
        image = cv2.imread(str(dataset / row["image"]))
        height, width = image.shape[:2]
        labels = []
        for line in (dataset / row["label"]).read_text().splitlines():
            role, x, y, w, h = map(float, line.split())
            labels.append({"role": NAMES[int(role)], "xyxy": [(x-w/2)*width, (y-h/2)*height, (x+w/2)*width, (y+h/2)*height]})
        prediction = model.predict(image, imgsz=image_size, conf=confidence, iou=.7, max_det=300, device=0, verbose=False)[0]
        predictions = [{"role": NAMES[int(role)], "xyxy": box} for box, role in zip(prediction.boxes.xyxy.cpu().tolist(), prediction.boxes.cls.cpu().tolist())]
        counts, unmatched = frame_confusion(labels, predictions)
        confusion.update(counts)
        extras.update(unmatched)
        frames += 1
    return {**operating_metrics(confusion, extras), "frames": frames, "confidence": confidence,
            "matching_iou": .5, "note": "Same provided/agent labels for both models; not independent ground truth. No field-boundary filtering in detector-only evaluation."}


def compare(root, dataset, protocol_path, run, output):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = verify_dataset(root, dataset, protocol_path)
    status = json.loads((run / "status.json").read_text())
    if status["status"] != "complete" or status["protocol_sha256"] != digest(protocol_path) or status["manifest_sha256"] != digest(dataset / "manifest.json"):
        raise ValueError("Incomplete or stale training run")
    baseline_spec = protocol.get("comparison_baseline", protocol["models"][0])
    paths = {"baseline": checked(root, baseline_spec["path"], baseline_spec["sha256"]),
             "balanced": checked(root, status["best_weights"], status["best_weights_sha256"])}
    if output.exists():
        raise FileExistsError(output)
    torch = setup(root)
    output.mkdir(parents=True)
    results = {key: {} for key in paths}
    with (output / "evaluation.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for key, path in paths.items():
            results[key]["validation"] = evaluate(path, dataset, protocol, output, "val", key+"_validation")
            results[key]["validation_fixed_confidence"] = fixed_confidence(path, dataset, manifest, "val", protocol["runtime_confidence"], protocol["image_size"])
            gc.collect()
            torch.cuda.empty_cache()
        decision = validation_choice(results["baseline"]["validation"], results["balanced"]["validation"], protocol["validation_gate"])
        write_json(output / "selection-before-test.json", {**decision, "validation": results,
                   "protocol_sha256": digest(protocol_path), "weights_sha256": {key: digest(path) for key, path in paths.items()}})
        for key, path in paths.items():
            results[key]["known_regression_test"] = evaluate(path, dataset, protocol, output, "test", key+"_test")
            results[key]["test_fixed_confidence"] = fixed_confidence(path, dataset, manifest, "test", protocol["runtime_confidence"], protocol["image_size"])
            gc.collect()
            torch.cuda.empty_cache()
    verify_dataset(root, dataset, protocol_path)
    if digest(paths["baseline"]) != baseline_spec["sha256"] or digest(paths["balanced"]) != status["best_weights_sha256"]:
        raise ValueError("Weights changed during comparison")
    report = {"kind": "balanced_role_comparison_v2", "protocol_sha256": digest(protocol_path),
              "manifest_sha256": digest(dataset / "manifest.json"), "selection": decision, "models": results,
              "training": status, "pipeline_promoted": False, "independently_validated": False,
              "test_previously_inspected": True, "images": manifest["images"], "excluded_base_images": manifest["excluded_base_images"]}
    write_json(output / "result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    paths = [path.resolve() for path in (args.dataset, args.run, args.output)]
    if any(not path.is_relative_to(root) for path in paths):
        raise ValueError("Paths must stay inside workspace")
    compare(root, paths[0], checked(root, args.protocol), paths[1], paths[2])
