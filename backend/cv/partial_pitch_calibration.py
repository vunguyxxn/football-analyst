"""Model-guided observed lines: calibrate visible midfield or penalty area.

Keypoints only select search strips. Four observed straight lines fit the
matrix; disjoint curved paint and the caller's full marking check validate it.
No hand labels, hidden corners or inferred players participate in fitting.
"""
import itertools
from collections import Counter

import cv2
import numpy as np

from backend.cv.pitch_circle_keypoints import white_pitch_pixels
from backend.cv.pitch_keypoints import project
from backend.cv.pitch_boundary import pitch_region


def _line(pixels, xy, confidence, indices, ends, size, segments, horizontal=False):
    width, height = size
    seeds = np.array([xy[i] for i in indices if confidence[i] >= .6 and np.isfinite(xy[i]).all()
                      and 4 <= xy[i, 0] < width-4 and 4 <= xy[i, 1] < height-4])
    if not len(seeds):
        raise ValueError("no_visible_seed")
    if len(seeds) >= 2:
        a, b = max(itertools.combinations(seeds, 2), key=lambda pair: np.linalg.norm(pair[1]-pair[0]))
        if np.linalg.norm(b-a) < 45:
            raise ValueError("short_seed_baseline")
        direction = b-a
    else:
        direction = None if not horizontal else np.array([1., 0.])
    ranked = []
    for x1, y1, x2, y2 in segments:
        start, stop = np.array([x1, y1], float), np.array([x2, y2], float)
        vector = stop-start
        length = np.linalg.norm(vector)
        vector /= length
        if not horizontal and abs(vector[1]) < .3:
            continue
        if direction is not None and abs(vector @ (direction/np.linalg.norm(direction))) < np.cos(np.deg2rad(35)):
            continue
        normal = np.array([-vector[1], vector[0]])
        line = np.r_[normal, -normal @ start]
        along = (seeds-start) @ vector
        errors = np.abs(np.c_[seeds, np.ones(len(seeds))] @ line)
        nearby = (along >= -60) & (along <= length+60)
        if not np.any(nearby) or np.min(errors[nearby]) > 60:
            continue
        if horizontal and len(seeds) >= 2 and (np.median(errors) > 30 or np.max(errors) > 60):
            continue
        score = length-3*np.min(errors[nearby])
        ranked.append((score, line, start, vector, length))
    hypotheses = []
    for _, line, start, direction, length in sorted(ranked, key=lambda item: -item[0]):
        if any(abs(line[:2] @ r["line"][:2]) > np.cos(np.deg2rad(2))
               and abs(np.r_[seeds.mean(axis=0), 1] @ (line-np.sign(line[:2] @ r["line"][:2])*r["line"])) < 8 for r in hypotheses):
            continue
        along = (pixels-start) @ direction
        support = pixels[(np.abs(np.c_[pixels, np.ones(len(pixels))] @ line) <= 2.5)
                         & (along >= -30) & (along <= length+30)]
        if len(support) < 100 or np.linalg.norm(np.ptp(support, axis=0)) < 120:
            continue
        vx, vy, cx, cy = cv2.fitLine(support, cv2.DIST_HUBER, 0, .001, .001).ravel()
        line = np.array([-vy, vx, vy*cx-vx*cy], float)
        hypotheses.append({"line": line, "ends": ends})
        if len(hypotheses) == 3:
            break
    if not hypotheses:
        raise ValueError("no_observed_line")
    return hypotheses


def _matrix(xs, ys, x_values, y_values):
    source, target = [], []
    for i, j in ((0, 0), (1, 0), (1, 1), (0, 1)):
        point = np.cross(xs[i], ys[j])
        if abs(point[2]) < .05:
            raise ValueError("unstable_intersection")
        source.append(point[:2]/point[2])
        target.append([x_values[i], y_values[j]])
    matrix, _ = cv2.findHomography(np.asarray(source), np.asarray(target), 0)
    if matrix is None or not np.isfinite(matrix).all():
        raise ValueError("invalid_matrix")
    forward = np.linalg.inv(matrix)
    den = np.c_[[0, 105, 105, 0], [0, 0, 68, 68], np.ones(4)] @ forward[2]
    if not (np.all(den > 1e-9) or np.all(den < -1e-9)):
        raise ValueError("pitch_horizon_crossing")
    points = project(forward, [[52.5, 34], [53.5, 34], [52.5, 35]])
    if points[1, 0] <= points[0, 0] or points[2, 1] >= points[0, 1]:
        raise ValueError("mirrored_pitch")
    return matrix/np.linalg.norm(matrix)


def _visible(matrix, world, size, lines=None):
    xy = project(np.linalg.inv(matrix), world)
    width, height = size
    good = (xy[:, 0] >= 4) & (xy[:, 0] < width-4) & (xy[:, 1] >= 4) & (xy[:, 1] < height-4)
    xy = xy[good]
    if lines is not None and len(xy):
        xy = xy[np.min(np.abs(np.c_[xy, np.ones(len(xy))] @ np.asarray(lines).T), axis=1) > 8]
    return xy


def _paint_check(xy, distance, minimum=30, fraction=.65):
    if len(xy) < minimum or np.linalg.norm(np.ptp(xy, axis=0)) < 90:
        return False
    x, y = np.rint(xy).astype(int).T
    residual = distance[y, x]
    return bool(np.median(residual) <= 4 and np.mean(residual <= 5) >= fraction)


def _independent_curve(matrix, pixels, size, lines, distance):
    theta = np.linspace(0, 2*np.pi, 360, endpoint=False)
    circle = _visible(matrix, np.c_[52.5+9.15*np.cos(theta), 34+9.15*np.sin(theta)], size, lines)
    if len(circle) >= 40:
        return _paint_check(circle, distance, 40, .75)
    # Penalty arcs are used only for validation, never to fit these matrices.
    theta = np.linspace(0, 2*np.pi, 720, endpoint=False)
    for center, front, side in ((11., 16.5, 1), (94., 88.5, -1)):
        world = np.c_[center+9.15*np.cos(theta), 34+9.15*np.sin(theta)]
        world = world[(world[:, 0]-front)*side >= 0]
        if _paint_check(_visible(matrix, world, size, lines), distance, 40, .75):
            return True
    return False


def fit_partial_pitch(frame, xy, confidence, *, quality, pixels=None):
    rejected = {"status": "rejected", "reason": "no_supported_partial_pitch", "matrix": None}
    if frame is None:
        return rejected
    xy, confidence = np.asarray(xy, float), np.asarray(confidence, float)
    if (xy.shape != (32, 2) or confidence.shape != (32,) or not np.isfinite(confidence).all()
            or np.any((confidence < 0) | (confidence > 1))):
        return rejected
    size = (frame.shape[1], frame.shape[0])
    if pixels is None:
        pixels = white_pitch_pixels(frame)
    if len(pixels) < 300:
        return rejected
    mask = np.ones(frame.shape[:2], np.uint8)
    xx, yy = pixels.astype(int).T
    mask[yy, xx] = 0
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    hough = cv2.HoughLinesP((1-mask)*255, 1, np.pi/720, 40, minLineLength=100, maxLineGap=20)
    if hough is None:
        return rejected
    segments = hough.reshape(-1, 4)
    xs, ys = {}, {}
    vertical = [(0., range(6), [[0, 0], [0, 68]]), (5.5, [6, 7], [[5.5, 24.84], [5.5, 43.16]]),
                (16.5, [9, 10, 11, 12], [[16.5, 13.84], [16.5, 54.16]]),
                (52.5, [13, 14, 15, 16], [[52.5, 0], [52.5, 68]]),
                (88.5, [17, 18, 19, 20], [[88.5, 13.84], [88.5, 54.16]]),
                (99.5, [22, 23], [[99.5, 24.84], [99.5, 43.16]]), (105., range(24, 30), [[105, 0], [105, 68]])]
    horizontal = [(68., [0, 13, 24], [[0, 68], [105, 68]]), (0., [5, 16, 29], [[0, 0], [105, 0]])]
    for side, offset, goal, front, small in (("left", 0, 0., 16.5, 5.5), ("right", 24, 105., 88.5, 99.5)):
        front_indices = [9, 12] if side == "left" else [17, 20]
        small_indices = [6, 7] if side == "left" else [22, 23]
        for y, a, b in ((54.16, 1+offset, front_indices[0]), (13.84, 4+offset, front_indices[1]),
                        (43.16, 2+offset, small_indices[0]), (24.84, 3+offset, small_indices[1])):
            horizontal.append(((side, y), [a, b], [[goal, y], [front if y in (54.16, 13.84) else small, y]]))
    for key, indices, ends in vertical:
        try:
            xs[key] = _line(pixels, xy, confidence, indices, ends, size, segments)
        except ValueError:
            pass
    for key, indices, ends in horizontal:
        try:
            ys[key] = _line(pixels, xy, confidence, indices, ends, size, segments, True)
        except ValueError:
            pass
    # The existing boundary detector can resolve a long advertising edge vs
    # the actual touchline. These are observed white edges, not grass-only or
    # model-extrapolated boundaries. Partial-box patterns still work without it.
    region = pitch_region(frame)
    if region is not None:
        edges = []
        for a, b in zip(region, np.roll(region, -1, axis=0)):
            delta = b-a
            if abs(delta[0]) < .25*size[0] or abs(delta[1]/delta[0]) > .3:
                continue
            normal = np.array([-delta[1], delta[0]])/np.linalg.norm(delta)
            edges.append(((a[1]+b[1])/2, np.r_[normal, -normal @ a]))
        if len(edges) >= 2:
            for key, (_, line) in zip((68., 0.), (min(edges, key=lambda r: r[0]), max(edges, key=lambda r: r[0]))):
                records = [{"line": line, "ends": [[0, key], [105, key]]}]
                ys[key] = records+ys.get(key, [])[:2]
    patterns = []
    for side, front, goal, small in (("left", 16.5, 0., 5.5), ("right", 88.5, 105., 99.5)):
        mid_y = [0., 68., (side, 54.16), (side, 13.84)]
        patterns.extend(((52.5, front), pair) for pair in itertools.combinations(mid_y, 2))
        for x_pair in ((goal, front), (small, front), (goal, small)):
            patterns.append((x_pair, ((side, 13.84), (side, 54.16))))
            patterns.append((x_pair, ((side, 24.84), (side, 43.16))))
    solutions, failures = [], Counter()
    diagnostics = []
    for x_keys, y_keys in patterns:
        if not all(k in xs for k in x_keys) or not all(k in ys for k in y_keys):
            continue
        for records in itertools.product(*[xs[k] for k in x_keys], *[ys[k] for k in y_keys]):
            lines = [r["line"] for r in records]
            try:
                matrix = _matrix(lines[:2], lines[2:], x_keys, [k[1] if isinstance(k, tuple) else k for k in y_keys])
                if not all(_paint_check(_visible(matrix, np.linspace(*r["ends"], 240), size), distance) for r in records):
                    failures["fitted_paint"] += 1
                    continue
                if not _independent_curve(matrix, pixels, size, lines, distance):
                    failures["disjoint_curve"] += 1
                    continue
                validation = quality(frame, matrix)
                if not validation["passed"]:
                    failures["visible_markings"] += 1
                    if len(diagnostics) < 3:
                        diagnostics.append({"x": x_keys, "y": [str(k) for k in y_keys], "failed": [r for r in validation.get("markings", []) if not r["passed"]]})
                    continue
                solutions.append(matrix)
            except (ValueError, np.linalg.LinAlgError, cv2.error) as error:
                failures[str(error)] += 1
    if not solutions:
        return {**rejected, "observed_x_lines": list(xs), "observed_y_lines": [str(k) for k in ys], "failures": dict(failures), "diagnostics": diagnostics}
    # Several supported patterns may describe the same field. Conflicting metre
    # coordinates are not resolved using a hand-labelled checkpoint or score.
    grid = np.array(list(itertools.product(np.linspace(4, size[0]-5, 8), np.linspace(4, size[1]-5, 6))))
    try:
        base = project(solutions[0], grid)
        inside = (base[:, 0] >= 0) & (base[:, 0] <= 105) & (base[:, 1] >= 0) & (base[:, 1] <= 68)
        if not np.any(inside):
            return {**rejected, "reason": "no_visible_ground"}
        if any(np.max(np.linalg.norm(project(m, grid[inside])-base[inside], axis=1)) > 1 for m in solutions[1:]):
            return {**rejected, "reason": "ambiguous_partial_pitch"}
    except ValueError:
        return {**rejected, "reason": "unstable_visible_projection"}
    return {"status": "candidate", "reason": None, "matrix": solutions[0].tolist(),
            "consistent_patterns": len(solutions), "validation": "disjoint_curve_and_all_visible_markings"}
