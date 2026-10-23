"""Experimental line fit with common tilt and lateral line offsets."""
from __future__ import annotations

import numpy as np

from backend.tactics.formation_templates import CATALOG, normalize


POLICY = {"catalog": list(CATALOG), "normalized_shears": [-.4, -.2, 0., .2, .4],
          "minimum_depth_m": 15., "minimum_width_m": 20.,
          "minimum_normalized_line_gap": .2, "lateral_offset_penalty": .1,
          "extra_line_penalty": .03, "maximum_score": .4, "minimum_margin": .05}


def aligned_shape(positions, goalkeeper_id, attack_direction):
    if attack_direction not in (-1, 1):
        raise ValueError("Invalid attack direction")
    if goalkeeper_id not in positions or len(positions) != 11:
        return {"status": "unknown", "reason": "need_eleven_including_goalkeeper"}
    all_xy = np.asarray(list(positions.values()), dtype=float)
    if all_xy.shape != (11, 2) or not np.isfinite(all_xy).all() or (all_xy < 0).any() or (all_xy > [105, 68]).any():
        raise ValueError("Positions must be finite and on pitch")
    ids = sorted(p for p in positions if p != goalkeeper_id)
    xy = np.asarray([positions[p] for p in ids], dtype=float)
    depth, width = float(np.ptp(xy[:, 0])), float(np.ptp(xy[:, 1]))
    base = {"centroid_m": xy.mean(axis=0).tolist(), "depth_m": depth, "width_m": width}
    if depth < POLICY["minimum_depth_m"] or width < POLICY["minimum_width_m"]:
        return {**base, "status": "unknown", "reason": "insufficient_spatial_extent"}
    relative = normalize(xy * [attack_direction, 1])
    candidates = []
    for shape in CATALOG:
        counts = list(map(int, shape.split("-")))
        best = None
        for shear in POLICY["normalized_shears"]:
            longitudinal = relative[:, 0] - shear * relative[:, 1]
            order = np.argsort(longitudinal, kind="stable")
            groups = np.split(order, np.cumsum(counts)[:-1])
            centers = np.asarray([longitudinal[g].mean() for g in groups])
            if (np.diff(centers) < POLICY["minimum_normalized_line_gap"]).any():
                continue
            targets = np.zeros(10)
            offsets = np.zeros(10)
            x_residual = np.zeros(10)
            for group, center in zip(groups, centers):
                ordered = group[np.argsort(relative[group, 1], kind="stable")]
                targets[ordered] = np.linspace(-1, 1, len(group)) if len(group) > 1 else 0.
                offsets[group] = relative[group, 1].mean()
                x_residual[group] = longitudinal[group] - center
            # Fit one width scale for all lines; individual centers may shift.
            denominator = float(targets @ targets)
            scale = float(targets @ (relative[:, 1] - offsets) / denominator)
            y_residual = relative[:, 1] - offsets - scale * targets
            score = float(np.sqrt(np.mean(x_residual ** 2 + y_residual ** 2)
                                  + POLICY["lateral_offset_penalty"] * np.mean(offsets ** 2)
                                  + POLICY["extra_line_penalty"] * (len(groups) - 3)))
            if best is None or score < best["score"]:
                best = {"shape": shape, "score": score, "shear": shear,
                        "groups": groups, "lateral_scale": scale}
        if best is not None:
            candidates.append(best)
    candidates.sort(key=lambda c: c["score"])
    if not candidates:
        return {**base, "status": "unknown", "reason": "no_separated_lines"}
    best = candidates[0]
    margin = candidates[1]["score"] - best["score"] if len(candidates) > 1 else None
    base.update(candidates=[{k: v for k, v in c.items() if k != "groups"} for c in candidates],
                score_margin=margin)
    if best["score"] > POLICY["maximum_score"]:
        return {**base, "status": "unknown", "reason": "poor_aligned_fit"}
    if margin is None or margin < POLICY["minimum_margin"]:
        return {**base, "status": "unknown", "reason": "ambiguous_aligned_shapes"}
    return {**base, "status": "observed_shape", "shape": best["shape"],
            "normalized_shear": best["shear"],
            "lines": [{"track_ids": [int(ids[i]) for i in group],
                       "centroid_m": xy[group].mean(axis=0).tolist()} for group in best["groups"]]}
