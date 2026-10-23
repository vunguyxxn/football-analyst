"""Offline step-5 report: observed formations and partial player profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from backend.common.schemas import TrackingRow
from backend.cv.metrica_benchmark import load_tracking
from backend.cv.pitch_metrics import PitchMetrics
from backend.tactics.formation import analyze_window


def player_profile(trajectory, start_s, stop_s, goalkeeper_id):
    """Reuse motion policy without labeling Metrica as AnalysisResult.video."""
    t = trajectory
    if not all(math.isfinite(v) for v in (start_s, stop_s, t.fps)) or stop_s <= start_s or t.fps <= 0:
        raise ValueError("Invalid period range or cadence")
    mask = (t.times >= start_s) & (t.times < stop_s)
    frames, times, xy, segments = t.frames[mask], t.times[mask], t.xy[mask], t.segments[mask]
    if not len(frames):
        raise ValueError("Player has no observations in window")
    if not np.isfinite(xy).all() or (xy < 0).any() or (xy > [105, 68]).any():
        raise ValueError("Player coordinates must be finite and on pitch")
    if (np.diff(frames) <= 0).any() or (np.diff(times) <= 0).any():
        raise ValueError("Frames/times must increase")
    metrics = PitchMetrics(t.fps)
    for i in range(len(frames)):
        # Explicitly break even short gaps; do not rely only on max_gap_s.
        if i and (frames[i] != frames[i - 1] + 1 or segments[i] != segments[i - 1]):
            metrics.break_chain(0, t.track_id)
        metrics.observe(0, TrackingRow(frame=int(frames[i]), time_s=float(times[i]),
                                      track_id=t.track_id, team=t.team,
                                      x_m=float(xy[i, 0]), y_m=float(xy[i, 1])))
    state = metrics.tracks[(0, t.track_id)]
    distance, duration = state["distance_m"], state["duration_s"]
    continuous = (np.diff(frames) == 1) & (np.diff(segments) == 0)
    observed_duration = float(np.diff(times)[continuous].sum())
    return {"track_id": t.track_id, "team": t.team, "is_goalkeeper": t.track_id == goalkeeper_id,
            "samples": len(frames), "sample_coverage": len(frames) / ((stop_s - start_s) * t.fps),
            "observed_continuous_duration_s": observed_duration,
            "represented_motion_duration_s": duration,
            "represented_window_fraction": duration / (stop_s - start_s),
            "observed_distance_m": distance,
            "mean_speed_kmh": distance / duration * 3.6 if duration else None,
            "max_speed_kmh": state["max_speed_kmh"] if duration else None,
            "rejected_motion_intervals": state["rejected_steps"],
            "continuity_breaks": int((~continuous).sum()),
            "median_position_m": np.median(xy, axis=0).tolist(),
            "heatmap_observed_frames": state["heatmap"]}


def team_report(trajectories, start_s, stop_s, window_s, goalkeeper_id, direction):
    if not math.isfinite(window_s) or window_s < 5 or stop_s - start_s < window_s:
        raise ValueError("Need at least one window of five seconds or more")
    if not trajectories or len({(t.game, t.team, t.fps) for t in trajectories}) != 1:
        raise ValueError("Need one nonempty team/game/cadence")
    if len({t.track_id for t in trajectories}) != len(trajectories):
        raise ValueError("Duplicate player identity")
    if goalkeeper_id not in {t.track_id for t in trajectories}:
        raise ValueError("Configured goalkeeper is absent")
    profiles = [player_profile(t, start_s, stop_s, goalkeeper_id)
                for t in sorted(trajectories, key=lambda t: t.track_id)]
    windows, start = [], start_s
    while start + window_s <= stop_s + 1e-9:
        windows.append(analyze_window(trajectories, start, start + window_s, goalkeeper_id, direction))
        start += window_s
    return {"team": trajectories[0].team, "goalkeeper_id": goalkeeper_id,
            "attack_direction": direction, "players": profiles, "formation_windows": windows,
            "formation_summary": {"total_windows": len(windows),
                                  "observed_shape_windows": sum(w["status"] == "observed_shape" for w in windows),
                                  "unknown_windows": sum(w["status"] == "unknown" for w in windows)},
            "unprocessed_formation_tail_s": max(0., stop_s - start)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/metrica"))
    parser.add_argument("--game", type=int, choices=(1, 2), required=True)
    parser.add_argument("--period", type=int, choices=(1, 2), default=1)
    parser.add_argument("--start", type=float, default=60)
    parser.add_argument("--stop", type=float, default=120)
    parser.add_argument("--window", type=float, default=10)
    parser.add_argument("--home-goalkeeper", type=int, required=True)
    parser.add_argument("--away-goalkeeper", type=int, required=True)
    parser.add_argument("--home-direction", type=int, choices=(-1, 1), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    data_dir, output = args.data_dir.resolve(), args.output.resolve()
    if not data_dir.is_relative_to(root) or not output.is_relative_to(root):
        parser.error("Paths must stay inside project")
    if output.exists():
        parser.error("Output already exists")
    if not all(math.isfinite(v) for v in (args.start, args.stop, args.window)) or args.start < 0 or args.window < 5 or args.stop - args.start < args.window:
        parser.error("Invalid time range/window")
    manifest = json.loads((root / "docs/fixtures/metrica_benchmark.json").read_text(encoding="utf-8"))
    sources, teams = [], []
    for team, side, goalkeeper, direction in (
        ("A", "Home", args.home_goalkeeper, args.home_direction),
        ("B", "Away", args.away_goalkeeper, -args.home_direction),
    ):
        source = (data_dir / f"Sample_Game_{args.game}_RawTrackingData_{side}_Team.csv").resolve()
        if not source.is_relative_to(root):
            parser.error("Source must stay inside project")
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        expected = next(f["sha256"] for f in manifest["files"] if f["filename"] == source.name)
        if digest != expected:
            parser.error(f"Source hash mismatch: {source.name}")
        trajectories, audit = load_tracking(source, args.game, team, args.start, args.stop, args.period)
        teams.append(team_report(trajectories, args.start, args.stop, args.window, goalkeeper, direction))
        sources.append({"path": source.relative_to(root).as_posix(), "sha256": digest,
                        "team": team, "loader_audit": audit})
    result = {"kind": "offline_metrica_tactics_v1", "game": args.game, "period": args.period,
              "start_s": args.start, "stop_s": args.stop, "window_s": args.window,
              "coordinate_system": "105x68_bottom_left", "sources": sources, "teams": teams,
              "motion_policy": {"interval_s": .5, "max_gap_s": 1., "max_speed_kmh": 40,
                                "break_on_every_missing_frame": True},
              "heatmap": {"columns": 21, "rows": 14, "origin": "bottom_left", "unit": "observed_frames"},
              "limitations": ["Partial source-coordinate metrics, not full-match totals or independent ground truth",
                              "Distance uses accepted 0.5s chords; gaps, rejected steps and tails are excluded",
                              "Observed spatial shapes are not validated tactical formations",
                              "No player identity mapping to StatsBomb"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"{sum(len(t['players']) for t in teams)} player profiles -> {output}")


if __name__ == "__main__":
    main()
