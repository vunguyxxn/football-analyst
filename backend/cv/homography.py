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


def refined_matrix_for(image_points, pitch_points, extra_image_points, extra_pitch_points):
    """Refine four manual anchors with >=2 extra controls, minimizing pixel error.

    Four-point mode is unchanged. Extra controls are calibration data, never
    held-out checks. Fit world -> image to avoid weighting distant pixels as
    if their metre-per-pixel scale were the same as nearby pixels.
    """
    matrix_for(image_points, pitch_points)
    image, pitch = [np.asarray(points, dtype=np.float64)
                    for points in (extra_image_points, extra_pitch_points)]
    if (image.ndim != 2 or image.shape[1:] != (2,) or image.shape[0] < 2
            or pitch.shape != image.shape or not np.isfinite(image).all()
            or not np.isfinite(pitch).all() or not (pitch >= 0).all()
            or not (pitch <= [105, 68]).all()):
        raise ValueError("Refinement requires >=2 finite image/pitch pairs inside the pitch")
    image = np.concatenate([image_points, image])
    pitch = np.concatenate([pitch_points, pitch])
    if len(np.unique(image, axis=0)) != len(image) or len(np.unique(pitch, axis=0)) != len(pitch):
        raise ValueError("Duplicate calibration controls")
    forward, _ = cv2.findHomography(pitch, image, method=0)
    if forward is None or not np.isfinite(forward).all() or np.linalg.matrix_rank(forward) != 3:
        raise ValueError("Singular refined homography")
    # Reject a projective horizon crossing the pitch, even if all controls fit.
    corners = np.array([[0, 0, 1], [105, 0, 1], [105, 68, 1], [0, 68, 1]])
    denominators = corners @ forward[2]
    if not (np.all(denominators > 1e-9) or np.all(denominators < -1e-9)):
        raise ValueError("Refined homography has a horizon inside the pitch")
    matrix = np.linalg.inv(forward)
    return matrix / np.linalg.norm(matrix)


class PitchCalibration:
    def __init__(self, source: Path, path: Path, width: int, height: int, compensate_camera=False,
                 landmark_checks: Path | None = None):
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
            if "extra_image_points" in segment or "extra_pitch_points" in segment:
                matrix = refined_matrix_for(points, segment["pitch_points"],
                                            segment.get("extra_image_points"), segment.get("extra_pitch_points"))
                extra = np.asarray(segment["extra_image_points"])
                if not ((extra >= 0).all() and (extra < [width, height]).all()):
                    raise ValueError("Refinement pixel points outside image")
            if not ((points >= 0).all() and (points < [width, height]).all()):
                raise ValueError("Calibration pixel points outside image")
            self.segments.append((index, start, stop, matrix))
            end = stop
        if not self.segments:
            raise ValueError("At least one calibrated range required")
        self.motion = None
        self.motion_frame = None
        if compensate_camera:
            from backend.cv.camera_motion import CameraMotion
            self.motion = CameraMotion()
        self.guard = None
        self.projection_verified = False
        if landmark_checks is not None:
            if not compensate_camera:
                raise ValueError("Landmark checks require camera compensation")
            from backend.cv.landmark_guard import LandmarkGuard
            self.guard = LandmarkGuard(landmark_checks, digest, width, height,
                                       [(start, stop) for _, start, stop, _ in self.segments])

    def prepare(self, frame_index, image, boxes):
        if self.motion is None:
            return {"status": "static"}
        self.motion_frame = frame_index
        for _, start, stop, matrix in self.segments:
            if start <= frame_index < stop:
                if self.guard is not None and frame_index == start:
                    self.guard.start_segment(start)
                quality = self.motion.update(image, boxes, anchor=matrix if frame_index == start else None)
                self.projection_verified = self.guard is None
                if self.guard is not None and self.motion.matrix is not None:
                    check = self.guard.check(frame_index, self.motion.matrix)
                    quality["landmark_check"] = check
                    self.projection_verified = check["status"] == "verified"
                    if check["status"] == "pending":
                        quality["status"] = "awaiting_landmark_check"
                    if check["status"] == "lost":
                        quality.update(status="lost", reason=check["reason"])
                        self.motion.failed = True
                        self.motion.matrix = self.motion.previous = self.motion.mask = None
                return quality
        return {"status": "uncalibrated"}

    def project(self, frame, fps, track_id, team, box):
        for index, start, stop, matrix in self.segments:
            if start <= frame < stop:
                if self.motion is not None:
                    if self.motion_frame != frame or self.motion.matrix is None or not self.projection_verified:
                        return None
                    matrix = self.motion.matrix
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
    parser.add_argument("--end-frame", type=int, required=True, help="Exclusive; use --compensate-camera in tracking for moving camera")
    parser.add_argument("--pitch-points", required=True, help='JSON e.g. [[0,0],[105,0],[105,68],[0,68]]')
    parser.add_argument("--extra-pitch-points", help="Optional JSON >=2 extra manual controls for refinement, clicked after the first four")
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error("Output must be a new file")
    pitch = json.loads(args.pitch_points)
    matrix_for([[0, 0], [1, 0], [1, 1], [0, 1]], pitch)
    extra_pitch = json.loads(args.extra_pitch_points) if args.extra_pitch_points else []
    if args.extra_pitch_points:
        extra_array = np.asarray(extra_pitch, dtype=float)
        if extra_array.ndim != 2 or extra_array.shape[1:] != (2,) or len(extra_array) < 2 or not np.isfinite(extra_array).all() or not ((extra_array >= 0).all() and (extra_array <= [105, 68]).all()):
            parser.error("Extra pitch controls must be >=2 finite pairs inside 105 x 68")
    required = 4 + len(extra_pitch)
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
    title = f"Pitch calibration: click {required} points; R reset; Enter save; Esc cancel"
    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < required:
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
            if key == 13 and len(points) == required:
                break
    finally:
        cv2.destroyAllWindows()
    matrix_for(points[:4], pitch)
    if extra_pitch:
        refined_matrix_for(points[:4], pitch, points[4:], extra_pitch)
    with args.source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    payload = {"source_sha256": digest, "image_size": [frame.shape[1], frame.shape[0]],
               "segments": [{"start_frame": args.frame, "end_frame": args.end_frame,
                             "image_points": points[:4], "pitch_points": pitch}]}
    if extra_pitch:
        payload["segments"][0].update(extra_image_points=points[4:], extra_pitch_points=extra_pitch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)


if __name__ == "__main__":
    main()
