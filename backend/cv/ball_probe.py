"""Offline feasibility probe for sports-ball detection, not an event detector."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def merge_candidates(candidates, threshold=.35):
    """Class-agnostic IoU NMS across overlapping crop detections."""
    kept = []
    for candidate in sorted(candidates, key=lambda item: -item["score"]):
        x1, y1, x2, y2 = candidate["xyxy"]
        area = (x2 - x1) * (y2 - y1)
        if area <= 0:
            continue
        duplicate = False
        for previous in kept:
            a, b, c, d = previous["xyxy"]
            intersection = max(0, min(x2, c) - max(x1, a)) * max(0, min(y2, d) - max(y1, b))
            union = area + (c - a) * (d - b) - intersection
            if union > 0 and intersection / union >= threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def detect_candidates(model, frame, *, device="0", tiled=True, confidence=.05):
    height, width = frame.shape[:2]
    classes = [key for key, name in model.names.items() if name in ("sports ball", "ball")]
    if not classes:
        raise ValueError("Local model has no sports ball class")
    regions = [(0, 0, width, height)]
    if tiled:
        crop_w, crop_h = max(32, round(width * .55)), max(32, round(height * .6))
        for y in (0, max(0, height - crop_h)):
            for x in (0, max(0, (width - crop_w) // 2), max(0, width - crop_w)):
                regions.append((x, y, min(width, x + crop_w), min(height, y + crop_h)))
    candidates = []
    for index, (left, top, right, bottom) in enumerate(regions):
        image = frame[top:bottom, left:right]
        result = model.predict(image, classes=classes, conf=confidence, imgsz=1280 if index == 0 else 960, device=device, verbose=False)[0]
        for box, score in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()):
            x1, y1, x2, y2 = box.tolist()
            candidates.append({"xyxy": [x1 + left, y1 + top, x2 + left, y2 + top],
                               "score": float(score), "view": "full" if index == 0 else f"tile-{index}"})
    return merge_candidates(candidates)


def probe(source: Path, output: Path, *, seconds=1., limit=60, tiled=True, weights=None):
    source, output = source.resolve(), output.resolve()
    if not source.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError("Paths must stay inside project")
    if output.exists() or not math.isfinite(seconds) or seconds <= 0 or not 1 <= limit <= 600:
        raise ValueError("Use a new output directory, positive cadence and 1–600 samples")
    config = ROOT / ".tmp/ultralytics"
    config.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config)
    import cv2
    import torch
    from ultralytics import YOLO
    from backend.cv.upload_analysis import video_info
    info = video_info(source)
    weights = Path(weights or ROOT / "data/raw/yolo11n.pt").resolve()
    if not weights.is_relative_to(ROOT) or not weights.is_file():
        raise ValueError("Local YOLO weights are missing")
    model = YOLO(str(weights))
    device = "0" if torch.cuda.is_available() else "cpu"
    output.mkdir(parents=True)
    samples = []
    capture = cv2.VideoCapture(str(source))
    try:
        for index, frame_id in enumerate(range(0, info["frames"], max(1, round(info["fps"] * seconds)))):
            if index >= limit:
                break
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ok, frame = capture.read()
            if not ok:
                raise ValueError("Cannot decode sampled frame")
            candidates = detect_candidates(model, frame, device=device, tiled=tiled)
            image_name = f"frame-{frame_id:06d}.jpg"
            # Keep raw images separate from predictions for independent labelling.
            cv2.imwrite(str(output / image_name), frame)
            samples.append({"frame": frame_id, "time_s": frame_id / info["fps"], "image": image_name,
                            "candidates": candidates})
            print(json.dumps({"frame": frame_id, "candidates": len(candidates)}), flush=True)
    finally:
        capture.release()
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with weights.open("rb") as stream:
        weights_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"kind": "ball_detection_probe_v1", "source": source.relative_to(ROOT).as_posix(),
              "source_sha256": digest, "weights_sha256": weights_hash, "video": info,
              "device": device, "confidence": .05, "tiled": tiled, "samples": samples,
              "sample_frames": len(samples), "frames_with_candidates": sum(bool(sample["candidates"]) for sample in samples),
              "warning": "Unlabelled detector candidates, not confirmed balls, recall or football events."}
    (output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=1.)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--no-tiles", action="store_true")
    parser.add_argument("--weights", type=Path)
    args = parser.parse_args()
    report = probe(args.source, args.output, seconds=args.seconds, limit=args.limit, tiled=not args.no_tiles, weights=args.weights)
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}))


if __name__ == "__main__":
    main()
