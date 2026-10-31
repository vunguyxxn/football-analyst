"""Offline research geometry; never publishes TrackingRow or calibrates uploads.

32-point order follows roboflow/sports SoccerFieldConfiguration.vertices.
See docs/AUTOMATIC_PITCH_KEYPOINTS.md for attribution and model provenance.
"""
from dataclasses import asdict, dataclass

import cv2
import numpy as np


LAYOUT = "sports32-105x68-bottom-left-v1"
# Keep regulation markings in metres, rather than scaling a 120x70 template.
PITCH_POINTS = np.array([
    (0, 68), (0, 54.16), (0, 43.16), (0, 24.84), (0, 13.84), (0, 0),
    (5.5, 43.16), (5.5, 24.84), (11, 34),
    (16.5, 54.16), (16.5, 43.16), (16.5, 24.84), (16.5, 13.84),
    (52.5, 68), (52.5, 43.15), (52.5, 24.85), (52.5, 0),
    (88.5, 54.16), (88.5, 43.16), (88.5, 24.84), (88.5, 13.84),
    (94, 34), (99.5, 43.16), (99.5, 24.84),
    (105, 68), (105, 54.16), (105, 43.16), (105, 24.84),
    (105, 13.84), (105, 0), (43.35, 34), (61.65, 34),
], dtype=np.float64)


@dataclass(frozen=True)
class FitPolicy:
    confidence: float = 0.6
    min_points: int = 6
    min_image_coverage: float = 0.02
    min_pitch_coverage: float = 0.03
    ransac_px: float = 5.0
    min_inlier_ratio: float = 0.7
    loo_median_px: float = 4.0
    loo_max_px: float = 12.0

    def json(self):
        return asdict(self)


def project(matrix, points):
    """Project without OpenCV's zero-denominator fallback."""
    points = np.asarray(points, dtype=np.float64)
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ matrix.T
    if not np.isfinite(homogeneous).all() or np.any(np.abs(homogeneous[:, 2]) < 1e-9):
        raise ValueError("Invalid projective denominator")
    return homogeneous[:, :2] / homogeneous[:, 2, None]


def coverage(points, area):
    return float(cv2.contourArea(cv2.convexHull(np.float32(points)))) / area


def fit_pitch(xy, confidence, image_size, policy=FitPolicy()):
    """Return a geometry candidate, not an accuracy or temporal validation.

    RANSAC and leave-one-out both use model predictions. Independent image
    landmarks must be checked separately; confidence is not metre accuracy.
    """
    xy, confidence = np.asarray(xy, dtype=float), np.asarray(confidence, dtype=float)
    if xy.shape != (32, 2) or confidence.shape != (32,):
        raise ValueError("Expected sports32 keypoints (32,2) and confidences (32,)")
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions")
    valid = (np.isfinite(xy).all(axis=1) & np.isfinite(confidence)
             & (confidence >= policy.confidence) & (confidence <= 1)
             & (xy[:, 0] >= 0) & (xy[:, 0] < width)
             & (xy[:, 1] >= 0) & (xy[:, 1] < height))
    ids = np.flatnonzero(valid)
    result = {"status": "rejected", "reason": "insufficient_points",
              "point_indices": ids.tolist(), "matrix": None}
    if len(ids) < policy.min_points:
        return result
    image, pitch = xy[ids], PITCH_POINTS[ids]
    distance = np.linalg.norm(image[:, None] - image[None, :], axis=2)
    if np.any(distance[np.triu_indices(len(image), 1)] < 2):
        return {**result, "reason": "duplicate_image_points"}
    if (coverage(image, width * height) < policy.min_image_coverage
            or coverage(pitch, 105 * 68) < policy.min_pitch_coverage):
        return {**result, "reason": "insufficient_coverage"}
    cv2.setRNGSeed(0)
    forward, mask = cv2.findHomography(pitch, image, cv2.RANSAC, policy.ransac_px)
    if forward is None or mask is None:
        return {**result, "reason": "homography_failed"}
    inliers = mask.ravel().astype(bool)
    result["inlier_indices"] = ids[inliers].tolist()
    result["inlier_ratio"] = float(np.mean(inliers))
    if inliers.sum() < policy.min_points or np.mean(inliers) < policy.min_inlier_ratio:
        return {**result, "reason": "insufficient_inliers"}
    image, pitch = image[inliers], pitch[inliers]
    if (coverage(image, width * height) < policy.min_image_coverage
            or coverage(pitch, 105 * 68) < policy.min_pitch_coverage):
        return {**result, "reason": "insufficient_inlier_coverage"}
    try:
        inverse = np.linalg.inv(forward)
        # Reject a projective horizon crossing the playing rectangle.
        corners = np.array([[0, 0, 1], [105, 0, 1], [105, 68, 1], [0, 68, 1]])
        denominators = corners @ forward[2]
        if not (np.all(denominators > 1e-8) or np.all(denominators < -1e-8)):
            return {**result, "reason": "pitch_horizon_crossing"}
        errors = []
        for i in range(len(pitch)):
            remaining = np.arange(len(pitch)) != i
            heldout, _ = cv2.findHomography(pitch[remaining], image[remaining], 0)
            if heldout is None:
                return {**result, "reason": "leave_one_out_degenerate"}
            errors.append(float(np.linalg.norm(project(heldout, pitch[i:i+1])[0] - image[i])))
        result["loo_median_px"] = float(np.median(errors))
        result["loo_max_px"] = max(errors)
        if np.median(errors) > policy.loo_median_px or max(errors) > policy.loo_max_px:
            return {**result, "reason": "leave_one_out_error"}
        inverse /= np.linalg.norm(inverse)
        if not np.isfinite(inverse).all():
            raise ValueError("Nonfinite inverse")
    except (ValueError, np.linalg.LinAlgError, cv2.error):
        return {**result, "reason": "invalid_projection"}
    return {**result, "status": "candidate", "reason": None, "matrix": inverse.tolist()}


def check_landmarks(matrix, checkpoint, max_error_m):
    """Evaluation only: never fit a matrix using these reference points."""
    try:
        predicted = project(np.asarray(matrix), checkpoint["image_points"])
        errors = np.linalg.norm(predicted - np.asarray(checkpoint["pitch_points"]), axis=1)
    except (ValueError, TypeError):
        return {"status": "failed", "reason": "invalid_projection"}
    return {"status": "passed" if np.max(errors) <= max_error_m else "failed",
            "max_error_m": float(np.max(errors)), "mean_error_m": float(np.mean(errors))}
