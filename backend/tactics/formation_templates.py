"""Heuristic relative-position templates, not learned or official tactics."""
from __future__ import annotations

import numpy as np


CATALOG = ("4-3-3", "4-4-2", "4-2-3-1", "4-1-4-1", "5-3-2", "3-5-2")
POLICY = {"maximum_normalized_rmse": .45, "minimum_score_margin": .08,
          "minimum_depth_m": 15., "minimum_width_m": 20., "catalog": list(CATALOG)}


def template_points(shape):
    counts = list(map(int, shape.split("-")))
    return np.asarray([(float(x), float(y))
                       for x, count in zip(np.linspace(-1, 1, len(counts)), counts)
                       for y in (np.linspace(-1, 1, count) if count > 1 else [0.])])


def normalize(points):
    centered = points - points.mean(axis=0)
    return centered / np.sqrt(np.mean(centered ** 2, axis=0))


def minimum_assignment(cost):
    """Exact square assignment via subset DP, at most 10 players (1024 states)."""
    n = len(cost)
    if cost.shape != (n, n) or not 1 <= n <= 10 or not np.isfinite(cost).all():
        raise ValueError("Need finite square cost matrix, size 1..10")
    scores = np.full(1 << n, np.inf)
    parents = np.full(1 << n, -1, dtype=int)
    scores[0] = 0.
    for mask in range(1 << n):
        row = mask.bit_count()
        if row == n:
            continue
        for column in range(n):
            if mask & (1 << column):
                continue
            new = mask | (1 << column)
            score = scores[mask] + cost[row, column]
            if score < scores[new]:
                scores[new], parents[new] = score, column
    assignment, mask = [], (1 << n) - 1
    for _ in range(n):
        column = int(parents[mask])
        assignment.append(column)
        mask ^= 1 << column
    return float(scores[-1]), assignment[::-1]


def template_shape(positions, goalkeeper_id, attack_direction, *, minimum_margin=.08):
    if attack_direction not in (-1, 1) or not np.isfinite(minimum_margin) or minimum_margin < 0:
        raise ValueError("Invalid direction or margin")
    if goalkeeper_id not in positions or len(positions) != 11:
        return {"status": "unknown", "reason": "need_eleven_including_goalkeeper"}
    all_xy = np.asarray(list(positions.values()), dtype=float)
    if all_xy.shape != (11, 2) or not np.isfinite(all_xy).all() or (all_xy < 0).any() or (all_xy > [105, 68]).any():
        raise ValueError("Positions must be finite and on pitch")
    ids = sorted(p for p in positions if p != goalkeeper_id)
    xy = np.asarray([positions[p] for p in ids], dtype=float)
    depth, width = float(np.ptp(xy[:, 0])), float(np.ptp(xy[:, 1]))
    base = {"centroid_m": xy.mean(axis=0).tolist(), "width_m": width, "depth_m": depth}
    if depth < POLICY["minimum_depth_m"] or width < POLICY["minimum_width_m"]:
        return {**base, "status": "unknown", "reason": "insufficient_spatial_extent"}
    relative = normalize(xy * [attack_direction, 1])
    candidates = []
    for shape in CATALOG:
        target = normalize(template_points(shape))
        cost = np.square(relative[:, None, :] - target[None, :, :]).sum(axis=2)
        sse, assignment = minimum_assignment(cost)
        candidates.append({"shape": shape, "normalized_rmse": float(np.sqrt(sse / 10)),
                           "assignment": assignment})
    candidates.sort(key=lambda item: item["normalized_rmse"])
    best = candidates[0]
    margin = candidates[1]["normalized_rmse"] - best["normalized_rmse"]
    base.update(candidates=[{k: v for k, v in c.items() if k != "assignment"} for c in candidates],
                score_margin=margin)
    if best["normalized_rmse"] > POLICY["maximum_normalized_rmse"]:
        return {**base, "status": "unknown", "reason": "poor_template_fit"}
    if margin < minimum_margin:
        return {**base, "status": "unknown", "reason": "ambiguous_templates"}
    # Slot membership is geometric, not a certified playing position/name.
    lines, offset = [], 0
    for count in map(int, best["shape"].split("-")):
        members = [i for i, slot in enumerate(best["assignment"]) if offset <= slot < offset + count]
        lines.append({"track_ids": [int(ids[i]) for i in members],
                      "centroid_m": xy[members].mean(axis=0).tolist()})
        offset += count
    return {**base, "status": "observed_shape", "shape": best["shape"], "lines": lines}
