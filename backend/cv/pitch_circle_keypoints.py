"""Offline, model-guided white-line/conic calibration; no manual anchors used.

YOLO circle points guide a search region, not fixed world correspondences.
Image ellipse extrema generally are NOT world cardinal points.
"""
from dataclasses import asdict, dataclass

import cv2
import numpy as np

from backend.cv.circle_calibration import circle_matrix, ellipse_conic
from backend.cv.pitch_keypoints import project


@dataclass(frozen=True)
class CirclePolicy:
    confidence: float = 0.6
    search_band_px: float = 80.
    max_center_shift_px: float = 100.
    max_edge_shift_px: float = 220.
    iterations: int = 700
    max_pixels: int = 4000
    min_circle_inliers: int = 300
    min_circle_fraction: float = 0.1
    min_arc_bins: int = 10  # Of 24; partial circles are explicitly permitted.
    circle_residual_px: float = 2.
    circle_refit_band_px: float = 4.
    circle_refit_iterations: int = 3
    field_line_median_px: float = 4.
    field_line_distance_px: float = 5.
    field_line_min_fraction: float = .65
    field_line_min_span_px: float = 120.

    def json(self):
        return asdict(self)


def conic_distance(ellipse, pixels):
    conic = ellipse_conic(ellipse)
    v = np.column_stack([pixels, np.ones(len(pixels))])
    return np.abs(np.sum((v @ conic) * v, axis=1)) / np.maximum(
        1e-9, np.linalg.norm(2 * v @ conic[:, :2], axis=1))


def white_pitch_pixels(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green = ((hsv[:, :, 0] > 30) & (hsv[:, :, 0] < 90) & (hsv[:, :, 1] > 60)).astype(np.float32)
    near_grass = cv2.boxFilter(green, -1, (31, 31)) > 0.45
    yy, xx = np.nonzero((hsv[:, :, 1] < 100) & (hsv[:, :, 2] > 150) & near_grass)
    return np.column_stack([xx, yy]).astype(np.float32)


def guided_line(pixels, center, direction, image_size, *, radius=None):
    """Find observed white support, rather than snapping to an invented line."""
    direction = np.asarray(direction, float)
    length = np.linalg.norm(direction)
    if not np.isfinite(length) or length < 1e-9:
        raise ValueError("invalid_line_direction")
    direction /= length
    normal = np.array([-direction[1], direction[0]])
    delta = pixels - center
    selected = np.abs(delta @ normal) < 80
    if radius is not None:
        selected &= np.linalg.norm(delta, axis=1) < radius
    points = pixels[selected]
    if len(points) < 100:
        raise ValueError("insufficient_line_pixels")
    width, height = image_size
    mask = np.zeros((height, width), np.uint8)
    x, y = points.astype(int).T
    mask[y, x] = 255
    segments = cv2.HoughLinesP(mask, 1, np.pi / 720, 40, minLineLength=70, maxLineGap=15)
    best = None
    if segments is not None:
        for x1, y1, x2, y2 in segments.reshape(-1, 4):
            start, stop = np.array([x1, y1], float), np.array([x2, y2], float)
            vector = stop - start
            length = np.linalg.norm(vector)
            vector /= length
            if abs(vector @ direction) < np.cos(np.deg2rad(12)):
                continue
            n = np.array([-vector[1], vector[0]])
            line = np.r_[n, -n @ start]
            score = length - 2 * abs(np.r_[center, 1] @ line)
            if best is None or score > best[0]:
                best = score, line
    if best is None:
        raise ValueError("no_observed_line")
    support = points[np.abs(np.c_[points, np.ones(len(points))] @ best[1]) < 2.5]
    if len(support) < 100 or np.linalg.norm(np.ptp(support, axis=0)) < 100:
        raise ValueError("insufficient_line_extent")
    vx, vy, cx, cy = cv2.fitLine(support, cv2.DIST_HUBER, 0, .01, .01).ravel()
    line = np.array([-vy, vx, vy * cx - vx * cy], float)
    return line


def fit_guided_circle(pixels, rough, halfway, policy):
    points = pixels[conic_distance(rough, pixels) < policy.search_band_px]
    points = points[np.abs(np.c_[points, np.ones(len(points))] @ halfway) > 8]
    rng = np.random.default_rng(0)
    if len(points) > policy.max_pixels:
        points = points[rng.choice(len(points), policy.max_pixels, replace=False)]
    if len(points) < policy.min_circle_inliers:
        raise ValueError("insufficient_circle_pixels")
    center, sizes, _ = rough
    minor, major = sorted(sizes)
    best = None
    for _ in range(policy.iterations):
        try:
            ellipse = cv2.fitEllipse(points[rng.choice(len(points), 8, replace=False)])
        except cv2.error:
            continue
        ctr, axes, _ = ellipse
        if (np.linalg.norm(np.array(ctr) - center) > policy.max_center_shift_px
                or not .5 * minor < min(axes) < 1.6 * minor
                or not .5 * major < max(axes) < 1.6 * major):
            continue
        inliers = conic_distance(ellipse, points) < policy.circle_residual_px
        if best is None or inliers.sum() > best.sum():
            best = inliers
    if best is None or best.sum() < max(policy.min_circle_inliers, len(points) * policy.min_circle_fraction):
        raise ValueError("circle_consensus_failed")
    ellipse = cv2.fitEllipse(points[best])
    # RANSAC may select just one edge of a thick painted stripe. Refit the
    # entire nearby stripe, so the conic follows its centre rather than edge.
    for _ in range(policy.circle_refit_iterations):
        stripe = points[conic_distance(ellipse, points) < policy.circle_refit_band_px]
        if len(stripe) < policy.min_circle_inliers:
            raise ValueError("circle_stripe_refit_failed")
        ellipse = cv2.fitEllipse(stripe)
    ctr, axes, _ = ellipse
    if (np.linalg.norm(np.array(ctr) - center) > policy.max_center_shift_px
            or not .5 * minor < min(axes) < 1.6 * minor
            or not .5 * major < max(axes) < 1.6 * major):
        raise ValueError("circle_refit_outside_prior")
    residual = conic_distance(ellipse, points)
    support = points[residual < policy.circle_residual_px]
    theta = np.deg2rad(ellipse[2])
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    normalized = (support - ellipse[0]) @ rotation / (np.array(ellipse[1]) / 2)
    angles = (np.arctan2(normalized[:, 1], normalized[:, 0]) + np.pi) / (2 * np.pi)
    bins = len(np.unique(np.minimum(23, (24 * angles).astype(int))))
    if bins < policy.min_arc_bins:
        raise ValueError("insufficient_circle_arc")
    return ellipse, {"circle_inlier_pixels": len(support), "circle_sample_pixels": len(points),
                     "arc_bins_of_24": bins, "circle_median_residual_px": float(np.median(residual[residual < 2]))}


def matrix_from_one_edge(ellipse, halfway, edge, edge_y):
    """Recover circle metric from conic, diameter and ONE observed touchline.

    The two circle crossings plus this outside-circle control determine the
    1D projectivity on the diameter. No unseen touchline is added as evidence.
    """
    conic = ellipse_conic(ellipse)
    line = np.asarray(halfway, float)
    edge = np.asarray(edge, float)
    if (edge_y not in (0, 68) or line.shape != (3,) or edge.shape != (2,)
            or not np.isfinite(line).all() or not np.isfinite(edge).all()
            or np.linalg.norm(line[:2]) < 1e-9):
        raise ValueError("invalid_diameter_control")
    if abs(np.r_[edge, 1.] @ line) / np.linalg.norm(line[:2]) > 1e-3:
        raise ValueError("edge_not_on_halfway_line")
    direction = np.array([-line[1], line[0], 0.])
    if direction[1] < 0:
        direction = -direction
    origin = np.r_[edge, 1.]
    roots = np.roots([direction @ conic @ direction, 2 * direction @ conic @ origin, origin @ conic @ origin])
    if len(roots) != 2 or np.any(np.abs(roots.imag) > 1e-6):
        raise ValueError("halfway_does_not_cross_circle")
    roots = np.sort(roots.real)
    if not ((edge_y == 68 and roots[0] > 0) or (edge_y == 0 and roots[1] < 0)):
        raise ValueError("touchline_not_outside_circle")
    points = np.array([edge, (origin + roots[0] * direction)[:2], (origin + roots[1] * direction)[:2]])
    world_y = [edge_y - 34, 9.15, -9.15]
    center, scale = points.mean(axis=0), max(np.linalg.norm(points[1] - points[2]), 1.)
    norm = np.array([[1 / scale, 0, -center[0] / scale], [0, 1 / scale, -center[1] / scale], [0, 0, 1.]])
    equations = []
    for pixel, y in zip(points, world_y):
        u, v = (pixel - center) / scale
        equations.extend([[y, 1, 0, 0, -u * y, -u], [0, 0, y, 1, -v * y, -v]])
    _, singular, vt = np.linalg.svd(equations)
    if singular[-2] < 1e-5:
        raise ValueError("degenerate_diameter_controls")
    a, b, c, d, e, f = vt[-1]
    hy, h0 = np.linalg.inv(norm) @ [a, c, e], np.linalg.inv(norm) @ [b, d, f]
    hx = np.cross(conic @ hy, conic @ h0)
    factor = (hy @ conic @ hy) / (hx @ conic @ hx)
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("invalid_circle_metric")
    hx *= np.sqrt(factor)
    if hx[0] * h0[2] - h0[0] * hx[2] < 0:
        hx = -hx
    forward = np.column_stack([hx, hy, h0]) @ np.array([[1, 0, -52.5], [0, 1, -34], [0, 0, 1]])
    corners = np.array([[0, 0, 1], [105, 0, 1], [105, 68, 1], [0, 68, 1]]) @ forward[2]
    if not (np.all(corners > 0) or np.all(corners < 0)):
        raise ValueError("pitch_horizon_crossing")
    inverse = np.linalg.inv(forward)
    inverse /= np.linalg.norm(inverse)
    if not np.isfinite(inverse).all():
        raise ValueError("invalid_projection")
    return inverse


def check_penalty_lines(matrix, pixels, image_size, policy):
    """Check disjoint visible white markings; never refit to this evidence.

    Circle/halfway agreement alone cannot establish accuracy far from midfield.
    Require a visible penalty-front line with substantial support as well.
    """
    width, height = image_size
    mask = np.ones((height, width), np.uint8)
    xx, yy = pixels.astype(int).T
    mask[yy, xx] = 0
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    forward = np.linalg.inv(matrix)
    checks = []
    for x in (16.5, 88.5):
        world = np.c_[np.full(300, x), np.linspace(13.84, 54.16, 300)]
        projected = project(forward, world)
        visible = projected[(projected[:, 0] >= 4) & (projected[:, 0] < width - 4)
                            & (projected[:, 1] >= 4) & (projected[:, 1] < height - 4)]
        if len(visible) < 30 or np.linalg.norm(visible[-1] - visible[0]) < policy.field_line_min_span_px:
            continue
        xx, yy = np.rint(visible).astype(int).T
        residual = distance[yy, xx]
        median = float(np.median(residual))
        fraction = float(np.mean(residual <= policy.field_line_distance_px))
        checks.append({"x_m": x, "sample_count": len(visible), "median_px": median,
                       "supported_fraction": fraction,
                       "passed": median <= policy.field_line_median_px and fraction >= policy.field_line_min_fraction})
    return {"status": "passed" if checks and all(c["passed"] for c in checks) else "failed" if checks else "not_evaluable",
            "lines": checks}


def fit_circle_pitch(frame, xy, confidence, policy=CirclePolicy()):
    result = {"status": "rejected", "reason": "insufficient_circle_seeds", "matrix": None}
    xy, confidence = np.asarray(xy, float), np.asarray(confidence, float)
    if xy.shape != (32, 2) or confidence.shape != (32,):
        raise ValueError("Expected 32 keypoints with confidences")
    height, width = frame.shape[:2]
    valid = (np.isfinite(xy).all(axis=1) & np.isfinite(confidence) & (confidence >= policy.confidence)
             & (confidence <= 1) & (xy[:, 0] >= 0) & (xy[:, 0] < width)
             & (xy[:, 1] >= 0) & (xy[:, 1] < height))
    if not (valid[14] and valid[15] and (valid[30] or valid[31])):
        return result
    endpoint_index = max((i for i in (31, 30) if valid[i]), key=lambda i: confidence[i])
    endpoint = xy[endpoint_index]
    center = xy[[14, 15]].mean(axis=0)
    delta = endpoint - center
    major, minor = 2 * np.linalg.norm(delta), np.linalg.norm(xy[15] - xy[14])
    if not (min(major, minor) > 40 and max(major, minor) < 1800):
        return {**result, "reason": "invalid_circle_prior"}
    rough = (tuple(center), (major, minor), float(np.rad2deg(np.arctan2(delta[1], delta[0])) % 180))
    try:
        pixels = white_pitch_pixels(frame)
        halfway = guided_line(pixels, center, xy[15] - xy[14], (width, height))
        ellipse, quality = fit_guided_circle(pixels, rough, halfway, policy)
        edges = {}
        for index, world_y in ((13, 68), (16, 0)):
            if not valid[index] or np.any(xy[index] < 0) or np.any(xy[index] >= [width, height]):
                continue
            direction = np.array([1., 0.])
            if valid[24] and index == 13:
                direction = xy[24] - xy[index]
            try:
                line = guided_line(pixels, xy[index], direction, (width, height), radius=260)
            except ValueError:
                continue
            cross = np.cross(halfway, line)
            if abs(cross[2]) < .05:
                continue
            point = cross[:2] / cross[2]
            if (np.any(point < 0) or np.any(point >= [width, height])
                    or np.linalg.norm(point - xy[index]) > policy.max_edge_shift_px):
                continue
            edges[world_y] = point
        if len(edges) == 2:
            matrix, diameter = circle_matrix(ellipse, edges[0], edges[68])
            quality.update(diameter)
        elif len(edges) == 1:
            y, point = next(iter(edges.items()))
            matrix = matrix_from_one_edge(ellipse, halfway, point, y)
        else:
            return {**result, "reason": "no_observed_touchline", **quality}
        # Roundtrip is numerical validation only, not independent accuracy.
        project(matrix, np.array(list(edges.values())))
        field_check = check_penalty_lines(matrix, pixels, (width, height), policy)
        quality["penalty_line_check"] = field_check
        if field_check["status"] != "passed":
            return {**result, "reason": "penalty_line_unsupported" if field_check["lines"] else "no_visible_penalty_line", **quality}
        return {**result, "status": "candidate", "reason": None, "matrix": matrix.tolist(),
                "ellipse": ellipse, "halfway_line": halfway.tolist(),
                "observed_touchlines": {str(y): p.tolist() for y, p in edges.items()}, **quality}
    except (ValueError, np.linalg.LinAlgError, cv2.error) as exc:
        return {**result, "reason": str(exc)}
