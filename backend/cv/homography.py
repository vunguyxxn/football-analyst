"""Manual, frame-scoped pitch calibration. Pixel coordinates stay internal."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from backend.common.schemas import TrackingRow


def matrix_for(image_points, pitch_points):
    arrays = [np.asarray(points, dtype=np.float64) for points in (image_points, pitch_points)]
    for points in arrays:
        if points.shape != (4, 2) or not np.isfinite(points).all():
            raise ValueError("Exactly four finite point pairs required")
        # Reject duplicates and any collinear triple (degenerate projective basis).
        for omitted in range(4):
            a, b, c = np.delete(points, omitted, axis=0)
            if abs(float(np.linalg.det(np.stack([b-a, c-a])))) < 1e-5:
                raise ValueError("Points must be distinct with no collinear triple")
    if not ((arrays[1] >= 0).all() and (arrays[1] <= [105, 68]).all()):
        raise ValueError("Pitch points must be inside 105 x 68 metres")
    matrix = cv2.getPerspectiveTransform(arrays[0].astype(np.float32), arrays[1].astype(np.float32))
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) != 3:
        raise ValueError("Singular homography")
    return matrix


class PitchCalibration:
    def __init__(self, source: Path, path: Path, width: int, height: int):
        payload = json.loads(path.read_text(encoding="utf-8"))
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if payload["source_sha256"] != digest or payload["image_size"] != [width, height]:
            raise ValueError("Calibration source hash or dimensions mismatch")
        self.segments = []
        end = 0
        for index, segment in enumerate(payload["segments"]):
            start, stop = segment["start_frame"], segment["end_frame"]
            if type(start) is not int or type(stop) is not int or start < end or stop <= start:
                raise ValueError("Calibration ranges must be ordered, disjoint, nonnegative [start, end)")
            points = np.asarray(segment["image_points"], dtype=float)
            matrix = matrix_for(points, segment["pitch_points"])
            if not ((points >= 0).all() and (points < [width, height]).all()):
                raise ValueError("Calibration pixel points outside image")
            self.segments.append((index, start, stop, matrix))
            end = stop
        if not self.segments:
            raise ValueError("At least one calibrated range required")

    def project(self, frame, fps, track_id, team, box):
        for index, start, stop, matrix in self.segments:
            if start <= frame < stop:
                # Foot contact proxy: bottom centre, never box centre.
                point = matrix @ np.array([(box[0]+box[2])/2, box[3], 1.0])
                if abs(point[2]) < 1e-9:
                    return None
                x, y = point[:2] / point[2]
                if not np.isfinite([x, y]).all() or not (0 <= x <= 105 and 0 <= y <= 68):
                    return None  # do not clamp off-field people onto touchlines
                return index, TrackingRow(frame=frame, time_s=frame/fps, track_id=int(track_id),
                                          team=team, x_m=float(x), y_m=float(y))
        return None


def main():
    parser = argparse.ArgumentParser(description="Click four known pitch points in matching order")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--end-frame", type=int, required=True, help="Exclusive; camera must stay fixed throughout range")
    parser.add_argument("--pitch-points", required=True, help='JSON e.g. [[0,0],[105,0],[105,68],[0,68]]')
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error("Output must be a new file")
    pitch = json.loads(args.pitch_points)
    matrix_for([[0, 0], [1, 0], [1, 1], [0, 1]], pitch)
    capture = cv2.VideoCapture(str(args.source))
    try:
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if not 0 <= args.frame < args.end_frame <= count:
            parser.error("Invalid frame range")
        capture.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
        ok, frame = capture.read()
        if not ok:
            parser.error("Cannot read calibration frame")
    finally:
        capture.release()
    points = []
    title = "Pitch calibration: click 4 points; R reset; Enter save; Esc cancel"
    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append([x, y])
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(title, click)
    try:
        while True:
            display = frame.copy()
            for i, point in enumerate(points):
                cv2.circle(display, tuple(point), 5, (0, 0, 255), -1)
                cv2.putText(display, str(i+1), tuple(point), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow(title, display)
            key = cv2.waitKey(30) & 255
            if key == 27 or cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                return
            if key in (ord('r'), ord('R')):
                points.clear()
            if key == 13 and len(points) == 4:
                break
    finally:
        cv2.destroyAllWindows()
    matrix_for(points, pitch)
    with args.source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    payload = {"source_sha256": digest, "image_size": [frame.shape[1], frame.shape[0]],
               "segments": [{"start_frame": args.frame, "end_frame": args.end_frame,
                             "image_points": points, "pitch_points": pitch}]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


if __name__ == "__main__":
    main()
