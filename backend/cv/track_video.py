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
                if classifier is None:
                    annotated = boxes.annotate(scene=frame, detections=detections)
                    annotated = labels.annotate(
                        scene=annotated, detections=detections,
                        labels=[f"ID {int(track_id)}" for track_id in detections.tracker_id],
                    )
                else:
                    import numpy as np

                    roles = [classifier.predict(frame, box.tolist()) for box in detections.xyxy]
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
    args = parser.parse_args()
    try:
        result = track_video(
            args.source, args.output, args.weights, device=args.device,
            chunk_seconds=args.chunk_seconds, confidence=args.confidence,
            image_size=args.image_size,
            team_samples=args.team_samples,
        )
    except (ValueError, FileNotFoundError, RuntimeError, ImportError) as error:
        parser.exit(1, f"Tracking failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
