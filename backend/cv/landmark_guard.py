"""Fail-closed, scheduled manual landmark checks; never fits a homography."""
import json
from pathlib import Path

import numpy as np


class LandmarkGuard:
    def __init__(self, path: Path, source_sha256, width, height, ranges):
        self.payload = json.loads(path.read_text(encoding="utf-8"))
        if self.payload.get("source_sha256") != source_sha256 or self.payload.get("image_size") != [width, height]:
            raise ValueError("Landmark checks source hash or dimensions mismatch")
        self.limit = self.payload.get("max_error_m", 1.0)
        self.max_gap = self.payload.get("max_gap_frames", 30)
        if (type(self.limit) not in (int, float) or not np.isfinite(self.limit) or self.limit <= 0
                or type(self.max_gap) is not int or self.max_gap < 1):
            raise ValueError("Landmark error limit and frame gap must be finite and positive")
        self.checkpoints = {}
        for row in self.payload.get("checkpoints", []):
            frame = row.get("frame")
            if (type(frame) is not int or frame in self.checkpoints
                    or not any(start < frame < stop for start, stop in ranges)):
                raise ValueError("Landmark check frame must be unique, inside a range and after its manual anchor")
            image, pitch = [np.asarray(row.get(key), dtype=float) for key in ("image_points", "pitch_points")]
            if (image.ndim != 2 or image.shape[1:] != (2,) or len(image) < 2 or pitch.shape != image.shape
                    or not np.isfinite(image).all() or not np.isfinite(pitch).all()
                    or not ((image >= 0).all() and (image < [width, height]).all())
                    or not ((pitch >= 0).all() and (pitch <= [105, 68]).all())
                    or len(np.unique(image, axis=0)) != len(image)
                    or len(np.unique(pitch, axis=0)) != len(pitch)):
                raise ValueError("Landmark check requires >=2 distinct finite image/pitch pairs inside bounds")
            self.checkpoints[frame] = image, pitch
        if not self.checkpoints:
            raise ValueError("At least one manual landmark checkpoint required")
        self.start_segment(0)

    def start_segment(self, start):
        self.start = start
        self.last_verified = None
        self.failed = False

    def check(self, frame, matrix):
        if self.failed:
            return {"status": "lost", "reason": "manual_anchor_required"}
        previous = self.last_verified if self.last_verified is not None else self.start
        # Do not revive an expired chain with a late check.
        if frame - previous > self.max_gap:
            self.failed = True
            return {"status": "lost", "reason": "landmark_check_expired"}
        if frame in self.checkpoints:
            image, pitch = self.checkpoints[frame]
            homogeneous = np.c_[image, np.ones(len(image))] @ matrix.T
            if np.any(np.abs(homogeneous[:, 2]) < 1e-9):
                self.failed = True
                return {"status": "lost", "reason": "invalid_landmark_projection"}
            projected = homogeneous[:, :2] / homogeneous[:, 2:]
            errors = np.linalg.norm(projected-pitch, axis=1)
            if not np.isfinite(errors).all():
                self.failed = True
                return {"status": "lost", "reason": "invalid_landmark_projection"}
            report = {"checkpoint_frame": frame, "errors_m": errors.tolist(),
                      "max_error_m": float(errors.max()), "limit_m": self.limit}
            if errors.max() > self.limit:
                self.failed = True
                return {"status": "lost", "reason": "landmark_drift_exceeded", **report}
            self.last_verified = frame
            return {"status": "verified", **report}
        if self.last_verified is None:
            return {"status": "pending", "reason": "awaiting_landmark_check"}
        return {"status": "verified", "checkpoint_frame": self.last_verified,
                "age_frames": frame-self.last_verified}
