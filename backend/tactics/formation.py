"""Conservative spatial-shape baseline; no tactical ground-truth claim."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from backend.cv.metrica_benchmark import load_tracking


def spatial_shape(positions, goalkeeper_id, attack_direction):
    """Group ten outfield median positions into longitudinal lines.

    Input/output locations remain in pitch coordinates. Only internal ordering
    uses attack direction; goalkeeper and direction must be supplied explicitly.
    """
    if attack_direction not in (-1, 1):
        raise ValueError("attack_direction must be -1 or 1")
    if goalkeeper_id not in positions or len(positions) != 11:
        return {"status": "unknown", "reason": "need_eleven_including_goalkeeper"}
    ids = [p for p in positions if p != goalkeeper_id]
    xy = np.asarray([positions[p] for p in ids], dtype=float)
    all_xy = np.asarray(list(positions.values()), dtype=float)
    if all_xy.shape != (11, 2) or not np.isfinite(all_xy).all() or (all_xy < 0).any() or (all_xy > [105, 68]).any():
        raise ValueError("Positions must be finite on-pitch coordinates")
    order = np.argsort(xy[:, 0] * attack_direction, kind="stable")
    gaps = np.diff(xy[order, 0] * attack_direction)
    base = {"centroid_m": xy.mean(axis=0).tolist(),
            "width_m": float(np.ptp(xy[:, 1])), "depth_m": float(np.ptp(xy[:, 0]))}
    # Borderline gaps are deliberately not converted to a confident label.
    if ((gaps >= 4) & (gaps <= 6)).any():
        return {**base, "status": "unknown", "reason": "borderline_line_separation"}
    groups = np.split(order, np.flatnonzero(gaps > 6) + 1)
    if len(groups) not in (3, 4) or any(len(g) > 5 or np.ptp(xy[g, 0]) > 12 for g in groups):
        return {**base, "status": "unknown", "reason": "unsupported_or_compact_shape"}
    return {**base, "status": "observed_shape", "shape": "-".join(str(len(g)) for g in groups),
            "lines": [{"track_ids": [int(ids[i]) for i in g],
                       "centroid_m": xy[g].mean(axis=0).tolist()} for g in groups]}


def analyze_window(trajectories, start_s, stop_s, goalkeeper_id, attack_direction, *, method="gap"):
    """Use only simultaneous full-roster frames; reject gaps/substitutions."""
    if method not in ("gap", "template"):
        raise ValueError("Unknown formation method")
    if not math.isfinite(start_s) or not math.isfinite(stop_s) or stop_s - start_s < 5:
        raise ValueError("Window must be finite and at least five seconds")
    if attack_direction not in (-1, 1):
        raise ValueError("attack_direction must be -1 or 1")
    base = {"start_s": start_s, "stop_s": stop_s, "goalkeeper_id": goalkeeper_id,
            "attack_direction": attack_direction}
    active = []
    for t in trajectories:
        mask = (t.times >= start_s) & (t.times < stop_s)
        if mask.any():
            active.append((t, mask))
    if len({t.track_id for t, _ in active}) != len(active):
        raise ValueError("Duplicate track identity")
    if len({t.team for t, _ in active}) > 1 or len({t.fps for t, _ in active}) > 1:
        raise ValueError("Window must contain one team and cadence")
    if len(active) != 11 or goalkeeper_id not in {t.track_id for t, _ in active}:
        return {**base, "status": "unknown", "reason": "incomplete_or_changed_roster"}
    expected = (stop_s - start_s) * active[0][0].fps
    maps = [{int(f): xy for f, xy in zip(t.frames[m], t.xy[m])} for t, m in active]
    common = sorted(set.intersection(*(set(v) for v in maps)))
    coverage = len(common) / expected
    base.update(joint_frames=len(common), joint_coverage=coverage)
    if coverage < .8:
        return {**base, "status": "unknown", "reason": "insufficient_joint_coverage"}
    positions = {t.track_id: np.median([v[f] for f in common], axis=0).tolist()
                 for (t, _), v in zip(active, maps)}
    from backend.tactics.formation_templates import template_shape

    recognizer = template_shape if method == "template" else spatial_shape
    return {**base, "players": [{"track_id": p, "median_position_m": xy,
                                  "is_goalkeeper": p == goalkeeper_id} for p, xy in positions.items()],
            **recognizer(positions, goalkeeper_id, attack_direction)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--game", type=int, choices=(1, 2), required=True)
    parser.add_argument("--team", choices=("A", "B"), required=True)
    parser.add_argument("--period", type=int, choices=(1, 2), default=1)
    parser.add_argument("--goalkeeper-id", type=int, required=True)
    parser.add_argument("--attack-direction", type=int, choices=(-1, 1), required=True)
    parser.add_argument("--start", type=float, default=60)
    parser.add_argument("--stop", type=float, default=120)
    parser.add_argument("--window", type=float, default=10)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source, output = args.input.resolve(), args.output.resolve()
    if not source.is_relative_to(root) or not output.is_relative_to(root):
        parser.error("Paths must stay inside project")
    if output.exists():
        parser.error("Output already exists")
    if not all(math.isfinite(v) for v in (args.start, args.stop, args.window)) or args.start < 0 or args.window < 5 or args.stop - args.start < args.window:
        parser.error("Invalid time range/window (minimum five seconds)")
    trajectories, audit = load_tracking(source, args.game, args.team, args.start, args.stop, args.period)
    results = []
    start = args.start
    while start + args.window <= args.stop + 1e-9:
        results.append(analyze_window(trajectories, start, start + args.window,
                                      args.goalkeeper_id, args.attack_direction))
        start += args.window
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"kind": "offline_spatial_shape_v1", "ground_truth_validated": False,
              "source_sha256": digest, "source_path": source.relative_to(root).as_posix(),
              "game": args.game, "team": args.team, "period": args.period,
              "parameters": {"minimum_joint_coverage": .8, "split_gap_m": 6,
                             "ambiguous_gap_m": [4, 6], "maximum_line_depth_m": 12},
              "coordinate_system": "105x68_bottom_left", "loader_audit": audit,
              "unprocessed_tail_s": max(0., args.stop - start), "windows": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"{len(results)} windows -> {output}")


if __name__ == "__main__":
    main()
