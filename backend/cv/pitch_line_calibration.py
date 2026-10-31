"""Offline four-line calibration. Circle pixels validate, not fit, the result."""
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from backend.cv.pitch_circle_keypoints import CirclePolicy, circle_hypothesis, guided_line, white_pitch_pixels
from backend.cv.pitch_keypoints import project


@dataclass(frozen=True)
class LinePolicy:
    seed: CirclePolicy = field(default_factory=CirclePolicy)
    min_visible_span_px: float = 120.
    min_white_fraction: float = .65
    max_median_px: float = 4.
    support_distance_px: float = 5.
    min_validation_samples: int = 40
    min_intersection_sine: float = .05

    def json(self):
        return asdict(self)


def fit_four_lines(halfway, penalty, far, near, penalty_x, policy=LinePolicy()):
    """Corresponding line intersections can lie outside the visible image.

    These are algebraic intersections, never claimed as observed keypoints.
    Each source line must separately have observed support before calling.
    """
    if penalty_x not in (16.5, 88.5):
        raise ValueError("invalid_penalty_side")
    lines = np.asarray([halfway, penalty, far, near], float)
    if lines.shape != (4, 3) or not np.isfinite(lines).all():
        raise ValueError("invalid_lines")
    sizes = np.linalg.norm(lines[:, :2], axis=1)
    if np.any(sizes < 1e-9):
        raise ValueError("degenerate_line")
    lines /= sizes[:, None]
    source = []
    for i, j in ((0, 2), (1, 2), (1, 3), (0, 3)):
        point = np.cross(lines[i], lines[j])
        if abs(point[2]) < policy.min_intersection_sine:
            raise ValueError("unstable_line_intersection")
        source.append(point[:2] / point[2])
    target = np.array([[52.5, 68], [penalty_x, 68], [penalty_x, 0], [52.5, 0]])
    matrix, _ = cv2.findHomography(np.array(source), target, 0)
    if matrix is None:
        raise ValueError("four_line_fit_failed")
    forward = np.linalg.inv(matrix)
    corners = np.c_[[0, 105, 105, 0], [0, 0, 68, 68], np.ones(4)] @ forward[2]
    if not (np.all(corners > 1e-9) or np.all(corners < -1e-9)):
        raise ValueError("pitch_horizon_crossing")
    matrix /= np.linalg.norm(matrix)
    if not np.isfinite(matrix).all():
        raise ValueError("invalid_projection")
    # Preserve image-right x and image-up y: no mirror solution accepted.
    center = project(forward, [[52.5, 34], [53.5, 34], [52.5, 35]])
    if center[1, 0] <= center[0, 0] or center[2, 1] >= center[0, 1]:
        raise ValueError("mirrored_pitch")
    return matrix


def visible_projection(forward, world, image_size):
    width, height = image_size
    pixels = project(forward, world)
    return pixels[(pixels[:, 0] >= 4) & (pixels[:, 0] < width - 4)
                  & (pixels[:, 1] >= 4) & (pixels[:, 1] < height - 4)]


def supported_line(pixels, seed_matrix, world_ends, image_size, policy):
    world = np.linspace(world_ends[0], world_ends[1], 300)
    projected = visible_projection(np.linalg.inv(seed_matrix), world, image_size)
    if len(projected) < 30 or np.linalg.norm(projected[-1] - projected[0]) < policy.min_visible_span_px:
        raise ValueError("insufficient_visible_line")
    line = guided_line(pixels, projected.mean(axis=0), projected[-1] - projected[0], image_size)
    # Require actual support near the finite projected segment too: a distant
    # advertisement or a short extrapolated fragment cannot qualify this line.
    direction = projected[-1] - projected[0]
    direction /= np.linalg.norm(direction)
    residual = np.abs(np.c_[pixels, np.ones(len(pixels))] @ line)
    along = (pixels - projected.mean(axis=0)) @ direction
    support = pixels[(residual < 2.5) & (np.abs(along) < np.linalg.norm(projected[-1] - projected[0]) / 2 + 30)]
    if len(support) < 100 or np.linalg.norm(np.ptp(support, axis=0)) < policy.min_visible_span_px:
        raise ValueError("insufficient_finite_line_support")
    return line


def check_circle(matrix, pixels, image_size, fit_lines, policy=LinePolicy()):
    """Validate on circle pixels away from fitted lines; never refit here."""
    theta = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    world = np.c_[52.5 + 9.15 * np.cos(theta), 34 + 9.15 * np.sin(theta)]
    projected = visible_projection(np.linalg.inv(matrix), world, image_size)
    if len(projected):
        distances = np.abs(np.c_[projected, np.ones(len(projected))] @ np.array(fit_lines).T)
        projected = projected[np.min(distances, axis=1) > 8]
    if len(projected) < policy.min_validation_samples:
        return {"status": "not_evaluable", "sample_count": len(projected)}
    width, height = image_size
    mask = np.ones((height, width), np.uint8)
    xx, yy = pixels.astype(int).T
    mask[yy, xx] = 0
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    xx, yy = np.rint(projected).astype(int).T
    residual = distance[yy, xx]
    median, fraction = float(np.median(residual)), float(np.mean(residual <= policy.support_distance_px))
    return {"status": "passed" if median <= policy.max_median_px and fraction >= policy.min_white_fraction else "failed",
            "sample_count": len(projected), "median_px": median, "supported_fraction": fraction}


def check_penalty_sides(matrix, pixels, image_size, penalty_x, policy=LinePolicy()):
    """Check penalty side edges (world y constant), never used by four-line fit."""
    width, height = image_size
    mask = np.ones((height, width), np.uint8)
    xx, yy = pixels.astype(int).T
    mask[yy, xx] = 0
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    forward = np.linalg.inv(matrix)
    goal_x = 0 if penalty_x == 16.5 else 105
    checks = []
    for y in (13.84, 54.16):
        world = np.c_[np.linspace(penalty_x, goal_x, 300), np.full(300, y)]
        projected = visible_projection(forward, world, image_size)
        if len(projected) < 30 or np.linalg.norm(projected[-1] - projected[0]) < policy.min_visible_span_px:
            continue
        xx, yy = np.rint(projected).astype(int).T
        residual = distance[yy, xx]
        median = float(np.median(residual))
        fraction = float(np.mean(residual <= policy.support_distance_px))
        checks.append({"y_m": y, "sample_count": len(projected), "median_px": median,
                       "supported_fraction": fraction,
                       "passed": median <= policy.max_median_px and fraction >= policy.min_white_fraction})
    return {"status": "passed" if checks and all(c["passed"] for c in checks) else "failed" if checks else "not_evaluable",
            "lines": checks}


def fit_line_pitch(frame, xy, confidence, policy=LinePolicy()):
    rejected = {"status": "rejected", "reason": "no_four_line_solution", "matrix": None}
    pixels = white_pitch_pixels(frame)
    seed = circle_hypothesis(frame, xy, confidence, policy.seed, pixels=pixels)
    if seed["status"] != "candidate":
        return {**rejected, "reason": "seed_" + seed["reason"]}
    size = (frame.shape[1], frame.shape[0])
    seed_matrix = np.asarray(seed["matrix"])
    try:
        far = supported_line(pixels, seed_matrix, [[0, 68], [105, 68]], size, policy)
        near = supported_line(pixels, seed_matrix, [[0, 0], [105, 0]], size, policy)
    except ValueError as exc:
        return {**rejected, "reason": "touchline_" + str(exc)}
    halfway = np.asarray(seed["halfway_line"])
    attempts, solutions = [], []
    for x in (16.5, 88.5):
        try:
            penalty = supported_line(pixels, seed_matrix, [[x, 13.84], [x, 54.16]], size, policy)
            matrix = fit_four_lines(halfway, penalty, far, near, x, policy)
            lines = [halfway, penalty, far, near]
            validation = check_circle(matrix, pixels, size, lines, policy)
            side_check = check_penalty_sides(matrix, pixels, size, x, policy)
            attempts.append({"penalty_x_m": x, "circle_check": validation, "penalty_side_check": side_check})
            if validation["status"] == "passed" and side_check["status"] == "passed":
                solutions.append({"matrix": matrix.tolist(), "penalty_x_m": x,
                                  "observed_lines": np.asarray(lines).tolist(), "circle_check": validation,
                                  "penalty_side_check": side_check})
        except (ValueError, np.linalg.LinAlgError, cv2.error) as exc:
            attempts.append({"penalty_x_m": x, "reason": str(exc)})
    if len(solutions) != 1:
        return {**rejected, "reason": "ambiguous_four_line_solutions" if solutions else "no_validated_four_line_solution",
                "attempts": attempts}
    return {**solutions[0], "status": "candidate", "reason": None, "attempts": attempts,
            "seed_used_for_search_only": True, "validation_not_independent_ground_truth": True}
