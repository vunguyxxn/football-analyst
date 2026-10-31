"""Bounded-memory, offline pitch-model evaluation; no upload/API integration."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import time

import cv2
import numpy as np

from backend.cv.pitch_keypoints import LAYOUT, FitPolicy, check_landmarks, fit_pitch
from backend.cv.pitch_circle_keypoints import CirclePolicy, fit_circle_pitch
from backend.cv.pitch_line_calibration import LinePolicy, fit_line_pitch

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS_SHA256 = "28f68f7c4056d6d9b137efd2e7ab5f3c494039380c63831649126ced25628b36"
MODEL_SOURCE = "https://github.com/roboflow/sports/blob/main/examples/soccer/setup.sh"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inputs(source, weights, checks, output):
    source, weights, checks, output = [Path(p).resolve() for p in (source, weights, checks, output)]
    if any(not p.is_relative_to(ROOT) for p in (source, weights, checks, output)):
        raise ValueError("All paths must be inside the workspace")
    if output.exists():
        raise ValueError("Use a new output directory; published artifacts must not be overwritten")
    if digest(weights) != WEIGHTS_SHA256:
        raise ValueError("Weights do not match the vendor-linked research checkpoint")
    reference = json.loads(checks.read_text(encoding="utf-8"))
    source_hash = digest(source)
    if reference["source_sha256"] != source_hash:
        raise ValueError("Reference landmarks belong to a different video")
    return source, weights, checks, output, reference, source_hash


def evaluate(source, weights, checks, output, stride=30, device="0", preprocess="stretch", method="keypoints"):
    if stride < 1:
        raise ValueError("stride must be positive")
    if preprocess not in ("stretch", "letterbox"):
        raise ValueError("Unknown preprocessing mode")
    if method not in ("keypoints", "circle", "lines"):
        raise ValueError("Unknown calibration method")
    source, weights, checks, output, reference, source_hash = inputs(source, weights, checks, output)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise ValueError("Cannot open source video")
    width, height = (int(capture.get(prop)) for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT))
    fps, frames = capture.get(cv2.CAP_PROP_FPS), int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    checkpoints = {item["frame"]: item for item in reference["checkpoints"]}
    if (reference["image_size"] != [width, height] or fps <= 0
            or len(checkpoints) != len(reference["checkpoints"])
            or any(not 0 <= frame < frames for frame in checkpoints)):
        capture.release()
        raise ValueError("Invalid reference dimensions/frames or duplicate checkpoints")
    for checkpoint in checkpoints.values():
        a, b = np.asarray(checkpoint["image_points"]), np.asarray(checkpoint["pitch_points"])
        if (a.ndim != 2 or a.shape[1:] != (2,) or len(a) < 2 or b.shape != a.shape
                or not np.isfinite(a).all() or not np.isfinite(b).all()
                or np.any(a < 0) or np.any(a >= [width, height])
                or np.any(b < 0) or np.any(b > [105, 68])):
            capture.release()
            raise ValueError("Invalid reference points")
    if not np.isfinite(reference["max_error_m"]) or reference["max_error_m"] <= 0:
        capture.release()
        raise ValueError("Invalid reference error limit")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".tmp" / "ultralytics"))
    os.environ.setdefault("TORCH_HOME", str(ROOT / ".tmp" / "torch"))
    import torch
    from ultralytics import YOLO
    model = YOLO(str(weights))
    if model.task != "pose" or list(model.model.yaml.get("kpt_shape", [])) != [32, 3]:
        capture.release()
        raise ValueError("Expected pose checkpoint with 32 confidence-bearing keypoints")
    gpu = device != "cpu"
    if gpu:
        torch.cuda.set_device(int(device))
        torch.cuda.reset_peak_memory_stats(int(device))
    output.mkdir(parents=True)
    policy = LinePolicy() if method == "lines" else CirclePolicy() if method == "circle" else FitPolicy()
    reasons, checks_summary = Counter(), Counter()
    timings, calibration_timings, evaluations = [], [], []
    index = samples = candidates = 0
    started = time.perf_counter()
    try:
        with (output / "frames.jsonl").open("w", encoding="utf-8") as stream:
            while capture.grab():
                if index % stride != 0 and index not in checkpoints:
                    index += 1
                    continue
                ok, frame = capture.retrieve()
                if not ok:
                    raise ValueError(f"Cannot decode frame {index}")
                before = time.perf_counter()
                model_input = cv2.resize(frame, (640, 640)) if preprocess == "stretch" else frame
                prediction = model.predict(model_input, imgsz=640,
                                           device=device, conf=0.25, verbose=False)[0]
                if gpu:
                    torch.cuda.synchronize(int(device))
                timings.append(time.perf_counter() - before)
                row = {"frame": index, "time_s": index / fps, "status": "rejected",
                       "reason": "ambiguous_or_missing_pitch", "matrix": None}
                if len(prediction.boxes) == 1 and prediction.keypoints is not None:
                    xy = prediction.keypoints.xy[0].cpu().numpy().astype(float)
                    if preprocess == "stretch":
                        xy *= [width / 640, height / 640]
                    confidence = prediction.keypoints.conf[0].cpu().numpy()
                    calibration_started = time.perf_counter()
                    if method == "lines":
                        row.update(fit_line_pitch(frame, xy, confidence, policy))
                    elif method == "circle":
                        row.update(fit_circle_pitch(frame, xy, confidence, policy))
                    else:
                        row.update(fit_pitch(xy, confidence, (width, height), policy))
                    calibration_timings.append(time.perf_counter() - calibration_started)
                    # Preserve raw output for reproducibility, not a public data contract.
                    row["keypoints"] = xy.tolist()
                    row["confidence"] = confidence.tolist()
                samples += 1
                candidates += row["status"] == "candidate"
                reasons[row["reason"] or "geometry_candidate"] += 1
                if index in checkpoints:
                    evaluation = {"frame": index, "status": "not_evaluable",
                                  "reason": row["reason"]}
                    if row["matrix"] is not None:
                        evaluation.update(check_landmarks(row["matrix"], checkpoints[index], reference["max_error_m"]))
                    row["reference_check"] = evaluation
                    checks_summary[evaluation["status"]] += 1
                    evaluations.append(evaluation)
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                index += 1
    finally:
        capture.release()
    if index != frames:
        raise ValueError(f"Decoded frame count differs: {index} != {frames}")
    report = {
        "status": "completed_offline_research", "source_sha256": source_hash,
        "weights_sha256": WEIGHTS_SHA256, "model_source": MODEL_SOURCE,
        "reference_sha256": digest(checks), "reference_status": reference.get("status"),
        "layout": LAYOUT, "method": method, "pitch_m": [105, 68], "policy": policy.json(),
        "checkpoint_metadata": {key: model.ckpt.get(key) for key in ("date", "version")},
        "checkpoint_training": {key: model.ckpt.get("train_args", {}).get(key)
                                for key in ("data", "imgsz", "epochs", "rect")},
        "preprocess": preprocess, "imgsz": 640,
        "image_size": [width, height], "fps": fps, "decoded_frames": index,
        "stride": stride, "samples": samples, "geometry_candidates": candidates,
        "reason_counts": dict(reasons), "reference_counts": dict(checks_summary),
        "reference_max_error_m": reference["max_error_m"], "reference_results": evaluations,
        "device": device, "gpu": torch.cuda.get_device_name(int(device)) if gpu else None,
        "torch_version": torch.__version__,
        "first_prediction_s": timings[0] if timings else None,
        "subsequent_prediction_mean_s": float(np.mean(timings[1:])) if len(timings) > 1 else None,
        "calibration_mean_s": float(np.mean(calibration_timings)) if calibration_timings else None,
        "peak_allocated_vram_mb": torch.cuda.max_memory_allocated(int(device)) / 2**20 if gpu else None,
        "elapsed_s": time.perf_counter() - started,
        "limitations": ["Sampled frames only; no continuous motion/stability validation",
                        "Model internal geometry consistency is not independent accuracy",
                        "Reference points are internal visual checks, not independent ground truth",
                        "No TrackingRow, heatmap, distance or production calibration published"],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=30)
    parser.add_argument("--device", default="0")
    parser.add_argument("--preprocess", choices=["stretch", "letterbox"], default="stretch")
    parser.add_argument("--method", choices=["keypoints", "circle", "lines"], default="keypoints")
    args = parser.parse_args()
    report = evaluate(**vars(args))
    print(json.dumps({key: report[key] for key in ("samples", "geometry_candidates", "reason_counts", "reference_counts")}))


if __name__ == "__main__":
    main()
