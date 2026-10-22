"""Run person detection and ByteTrack on a local video with bounded memory."""

from __future__ import annotations

import argparse
from copy import copy
import json
import math
from pathlib import Path
from time import perf_counter


def track_video(
    source: Path,
    output: Path,
    weights: Path,
    *,
    device: str = "0",
    chunk_seconds: float = 10,
    confidence: float = 0.1,
    image_size: int = 640,
    team_samples: Path | None = None,
    calibration: Path | None = None,
    pitch_output: Path | None = None,
    compensate_camera: bool = False,
) -> dict[str, object]:
    """Write an annotated silent MP4, processing one frame at a time.

    Chunks bound the processing loop without resetting the tracker or loading
    frame lists. IDs persist across chunk boundaries, but are not player
    identities and may change after occlusion or camera cuts.
    """
    source, output, weights = source.resolve(), output.resolve(), weights.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Video not found: {source}")
    if not weights.is_file():
        raise FileNotFoundError(f"Local YOLO weights not found: {weights}")
    if output == source or output == weights or output.exists():
        raise ValueError("Output must be a new file, distinct from input and weights")
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must use the .mp4 extension")
    if not math.isfinite(chunk_seconds) or chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be positive and finite")
    if not math.isfinite(confidence) or not 0 < confidence <= 1:
        raise ValueError("confidence must be in (0, 1]")
    if image_size < 32 or image_size % 32:
        raise ValueError("image_size must be a positive multiple of 32")
    if (calibration is None) != (pitch_output is None):
        raise ValueError("calibration and pitch_output must be supplied together")
    if pitch_output is not None and pitch_output.exists():
        raise ValueError("pitch_output must be a new directory")
    if compensate_camera and calibration is None:
        raise ValueError("Camera compensation requires manual calibration")

    # Keep CV dependencies optional for the existing StatsBomb backend.
    import cv2
    import supervision as sv
    import torch
    from ultralytics import YOLO

    if device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; check PyTorch or explicitly use --device cpu")
    model = YOLO(str(weights))
    person_classes = [key for key, name in model.names.items() if name == "person"]
    if not person_classes:
        raise ValueError("This step requires YOLO weights containing the 'person' class")

    classifier = None
    if team_samples is not None:
        from backend.cv.team_classifier import fit_from_samples

        classifier = fit_from_samples(source, team_samples)

    capture = cv2.VideoCapture(str(source))
    writer = None
    pitch_stream = None
    camera_stream = None
    projection = metrics = None
    projected_rows = 0
    frames = chunks = 0
    team_observations = {"A": 0, "B": 0, "referee": 0, "unknown": 0}
    started = perf_counter()
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open video: {source}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not math.isfinite(fps) or fps <= 0 or width <= 0 or height <= 0:
            raise ValueError("Video has invalid FPS or dimensions")
        if calibration is not None:
            from backend.cv.homography import PitchCalibration
            from backend.cv.pitch_metrics import PitchMetrics

            projection = PitchCalibration(source, calibration, width, height, compensate_camera)
            if any(stop > int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) for _, _, stop, _ in projection.segments):
                raise ValueError("Calibration range exceeds video length")
            metrics = PitchMetrics(fps)
            pitch_output.mkdir(parents=True, exist_ok=False)
            pitch_stream = (pitch_output / "tracking.jsonl").open("x", encoding="utf-8")
            if compensate_camera:
                camera_stream = (pitch_output / "camera_quality.jsonl").open("x", encoding="utf-8")
        chunk_frames = max(1, round(chunk_seconds * fps))
        tracker = sv.ByteTrack(frame_rate=max(1, round(fps)))
        boxes = sv.BoxAnnotator()
        labels = sv.LabelAnnotator()
        if classifier is not None:
            palette = sv.ColorPalette.from_hex(["#a855f7", "#22d3ee", "#facc15", "#94a3b8"])
            boxes = sv.BoxAnnotator(color=palette)
            labels = sv.LabelAnnotator(color=palette)
        output.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )
        if not writer.isOpened():
            raise RuntimeError(f"Cannot create output video: {output}")
        eof = False
        while not eof:
            chunk_count = 0
            for _ in range(chunk_frames):
                ok, frame = capture.read()
                if not ok:
                    eof = True
                    break
                result = model.predict(
                    frame, classes=person_classes, conf=confidence,
                    imgsz=image_size, device=device, verbose=False,
                )[0]
                detections = tracker.update_with_detections(
                    sv.Detections.from_ultralytics(result)
                )
                roles = ([classifier.predict(frame, box.tolist()) for box in detections.xyxy]
                         if classifier is not None else ["unknown"] * len(detections))
                if projection is not None:
                    quality = projection.prepare(frames, frame, result.boxes.xyxy.cpu().numpy() if compensate_camera else detections.xyxy)
                    if camera_stream is not None:
                        camera_stream.write(json.dumps({"frame": frames, **quality}) + "\n")
                    for box, track_id, role in zip(detections.xyxy, detections.tracker_id, roles):
                        projected = projection.project(frames, fps, track_id, role, box)
                        if projected is not None:
                            segment, row = projected
                            pitch_stream.write(row.model_dump_json() + "\n")
                            metrics.observe(segment, row)
                            projected_rows += 1
                    if compensate_camera:
                        cv2.putText(frame, f"Pitch: {quality['status']}", (20, 35),
                                    cv2.FONT_HERSHEY_SIMPLEX, .8,
                                    (0, 200, 0) if quality["status"] in ("tracked", "manual_anchor") else (0, 0, 255), 2)
                if classifier is None:
                    annotated = boxes.annotate(scene=frame, detections=detections)
                    annotated = labels.annotate(
                        scene=annotated, detections=detections,
                        labels=[f"ID {int(track_id)}" for track_id in detections.tracker_id],
                    )
                else:
                    import numpy as np

                    for role in roles:
                        team_observations[role] += 1
                    # supervision 0.26.1 compares custom_color_lookup arrays to
                    # an Enum with scalar truth testing. Use a drawing-only
                    # copy with role color indices; keep detector classes intact.
                    drawing_detections = copy(detections)
                    drawing_detections.class_id = np.array([list(team_observations).index(role) for role in roles], dtype=int)
                    annotated = boxes.annotate(scene=frame, detections=drawing_detections)
                    annotated = labels.annotate(
                        scene=annotated, detections=drawing_detections,
                        labels=[f"{role} ID {int(track_id)}" for role, track_id in zip(roles, detections.tracker_id)],
                    )
                writer.write(annotated)
                frames += 1
                chunk_count += 1
            if chunk_count:
                chunks += 1
        if not frames:
            raise ValueError("Video contains no decodable frames")
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if pitch_stream is not None:
            pitch_stream.close()
        if camera_stream is not None:
            camera_stream.close()
        if not frames and output.is_file():
            output.unlink()

    elapsed = perf_counter() - started
    summary = {
        "output": str(output), "frames": frames, "chunks": chunks,
        "video_fps": fps, "processing_fps": round(frames / elapsed, 2),
        "device": device, "weights": str(weights),
    }
    if classifier is not None:
        summary["team_observations"] = team_observations
        summary["team_samples"] = str(team_samples)
    if metrics is not None:
        report = metrics.report()
        report["source"] = str(source)
        report["camera_compensation"] = compensate_camera
        report["calibration"] = json.loads(calibration.read_text(encoding="utf-8"))
        (pitch_output / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["pitch_output"] = str(pitch_output)
        summary["projected_rows"] = projected_rows
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--device", default="0", help="CUDA index (default: 0) or cpu")
    parser.add_argument("--chunk-seconds", type=float, default=10)
    parser.add_argument("--confidence", type=float, default=0.1)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--team-samples", type=Path, help="Clip-specific calibration/evaluation annotations")
    parser.add_argument("--calibration", type=Path, help="Manual frame-scoped homography JSON")
    parser.add_argument("--pitch-output", type=Path, help="New directory for TrackingRow JSONL and metrics JSON")
    parser.add_argument("--compensate-camera", action="store_true", help="Track ground motion after each manual anchor; stop on quality loss")
    args = parser.parse_args()
    try:
        result = track_video(
            args.source, args.output, args.weights, device=args.device,
            chunk_seconds=args.chunk_seconds, confidence=args.confidence,
            image_size=args.image_size,
            team_samples=args.team_samples,
            calibration=args.calibration, pitch_output=args.pitch_output,
            compensate_camera=args.compensate_camera,
        )
    except (ValueError, FileNotFoundError, RuntimeError, ImportError) as error:
        parser.exit(1, f"Tracking failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
