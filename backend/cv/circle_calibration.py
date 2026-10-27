"""Experimental calibration from a manually located centre circle and halfway line.

An ellipse extremum is NOT assigned a world cardinal point. Recover the conic
and its diameter projectivity instead. Requires separate held-out controls.
"""
import cv2
import numpy as np


def ellipse_conic(ellipse):
    (cx, cy), (width, height), angle = ellipse
    if min(width, height) <= 0 or not np.isfinite([cx, cy, width, height, angle]).all():
        raise ValueError("Invalid ellipse")
    theta = np.deg2rad(angle)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    quadratic = rotation @ np.diag([4 / width**2, 4 / height**2]) @ rotation.T
    center = np.array([cx, cy])
    conic = np.zeros((3, 3))
    conic[:2, :2] = quadratic
    conic[:2, 2] = conic[2, :2] = -quadratic @ center
    conic[2, 2] = center @ quadratic @ center - 1
    return conic


def circle_matrix(ellipse, near, far, *, pitch_width=68., radius=9.15):
    near, far = np.asarray(near, float), np.asarray(far, float)
    conic = ellipse_conic(ellipse)
    if near.shape != (2,) or far.shape != (2,) or not np.isfinite([near, far]).all() or np.linalg.norm(near - far) < 20:
        raise ValueError("Invalid halfway-line touchline controls")
    direction = np.r_[near - far, 0.]
    origin = np.r_[far, 1.]
    roots = np.roots([direction @ conic @ direction, 2 * direction @ conic @ origin, origin @ conic @ origin])
    if np.any(np.abs(roots.imag) > 1e-6):
        raise ValueError("Halfway line does not cross centre circle")
    roots = np.sort(roots.real)
    if not (0 < roots[0] < roots[1] < 1):
        raise ValueError("Circle must lie between touchline controls")
    points = [far, near, far + roots[0] * (near - far), far + roots[1] * (near - far)]
    world_y = [pitch_width / 2, -pitch_width / 2, radius, -radius]
    # Normalize pixels for well-conditioned DLT of the diameter projectivity.
    center = np.mean(points, axis=0)
    scale = np.linalg.norm(near - far)
    norm = np.array([[1 / scale, 0, -center[0] / scale], [0, 1 / scale, -center[1] / scale], [0, 0, 1.]])
    equations = []
    for pixel, y in zip(points, world_y):
        x_img, y_img = (np.asarray(pixel) - center) / scale
        equations += [[y, 1, 0, 0, -x_img * y, -x_img], [0, 0, y, 1, -y_img * y, -y_img]]
    _, _, vt = np.linalg.svd(equations)
    a, b, c, d, e, f = vt[-1]
    hy, h0 = np.linalg.inv(norm) @ [a, c, e], np.linalg.inv(norm) @ [b, d, f]
    hx = np.cross(conic @ hy, conic @ h0)
    denominator = hx @ conic @ hx
    factor = (hy @ conic @ hy) / denominator
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("Cannot recover circle metric")
    hx *= np.sqrt(factor)
    if (hx[0] * h0[2] - h0[0] * hx[2]) < 0:
        hx = -hx
    forward = np.column_stack([hx, hy, h0]) @ np.array([[1, 0, -52.5], [0, 1, -pitch_width / 2], [0, 0, 1]])
    forward /= forward[2, 2]
    projected = cv2.perspectiveTransform(np.float64([[[52.5, y + pitch_width / 2] for y in world_y]]), forward)[0]
    error = float(np.max(np.linalg.norm(projected - points, axis=1)))
    if error > 3:
        raise ValueError(f"Diameter controls disagree with circle: {error:.2f}px")
    corners = np.array([[0, 0, 1], [105, 0, 1], [105, pitch_width, 1], [0, pitch_width, 1]]) @ forward[2]
    if not ((corners > 0).all() or (corners < 0).all()):
        raise ValueError("Projective horizon crosses pitch")
    return np.linalg.inv(forward), {"diameter_error_px": error, "ellipse": ellipse}


def fit_circle_pixels(frame, rough_ellipse):
    """Fit only near the manually selected ellipse; this is not automatic initialization."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    yy, xx = np.nonzero((hsv[:, :, 1] < 100) & (hsv[:, :, 2] > 165))
    points = np.c_[xx, yy].astype(np.float32)
    reference = ellipse_conic(rough_ellipse)
    homogeneous = np.c_[points, np.ones(len(points))]
    gradient = 2 * homogeneous @ reference[:, :2]
    distance = np.abs(np.sum((homogeneous @ reference) * homogeneous, axis=1)) / np.maximum(1e-9, np.linalg.norm(gradient, axis=1))
    points = points[distance < 7]
    if len(points) < 100:
        raise ValueError("Insufficient white centre-circle pixels")
    rng = np.random.default_rng(20261027)
    best = None
    for _ in range(200):
        candidate = cv2.fitEllipse(points[rng.choice(len(points), 8, replace=False)])
        (cx, cy), sizes, _ = candidate
        if np.linalg.norm(np.array([cx, cy]) - rough_ellipse[0]) > 30 or min(sizes) < 30 or max(sizes) > 1200:
            continue
        conic = ellipse_conic(candidate)
        vectors = np.c_[points, np.ones(len(points))]
        residual = np.abs(np.sum((vectors @ conic) * vectors, axis=1)) / np.maximum(1e-9, np.linalg.norm(2 * vectors @ conic[:, :2], axis=1))
        mask = residual < 1.8
        if best is None or mask.sum() > best.sum():
            best = mask
    if best is None or best.sum() < 100:
        raise ValueError("Centre circle fit failed")
    ellipse = cv2.fitEllipse(points[best])
    return ellipse, {"white_pixels": len(points), "inlier_pixels": int(best.sum())}
