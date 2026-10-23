"""Offline reference-trajectory benchmark; no detector/homography claims."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from backend.common.schemas import TrackingRow
from backend.cv.pitch_metrics import PitchMetrics
from backend.cv.pitch_smoother import PitchSmoother


@dataclass
class Trajectory:
    game: int
    track_id: int
    team: str
    frames: np.ndarray
    times: np.ndarray
    xy: np.ndarray
    segments: np.ndarray
    fps: float


def load_tracking(path, game, team, start_s, stop_s, period=1):
    """Read the three-header Metrica CSV, omit ball/NaN/off-pitch points."""
    columns = {}
    values = {}
    excluded = {"missing": 0, "outside": 0}
    native = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        next(reader)
        header = next(reader)
        if header[:3] != ["Period", "Frame", "Time [s]"]:
            raise ValueError("Unsupported Metrica CSV header")
        for i, name in enumerate(header):
            if name.startswith("Player"):
                player = int(name[6:]) + (1000 if team == "B" else 0)
                if player in columns:
                    raise ValueError("Duplicate player header")
                columns[player] = i
                values[player] = []
        if not columns:
            raise ValueError("No player columns")
        for cells in reader:
            if int(cells[0]) != period:
                continue
            frame, time_s = int(cells[1]), float(cells[2])
            if not start_s <= time_s < stop_s:
                continue
            if native and (frame <= native[-1][0] or time_s <= native[-1][1]):
                raise ValueError("CSV frames/times must increase within period")
            native.append((frame, time_s))
            for player, column in columns.items():
                x, y = float(cells[column] or "nan"), float(cells[column + 1] or "nan")
                if not math.isfinite(x) or not math.isfinite(y):
                    excluded["missing"] += 1
                elif not (0 <= x <= 1 and 0 <= y <= 1):
                    excluded["outside"] += 1
                else:
                    values[player].append((frame, time_s, x * 105, (1 - y) * 68))
    if len(native) < 2:
        raise ValueError("Need at least two frames in the requested window")
    fps = round((native[1][0] - native[0][0]) / (native[1][1] - native[0][1]), 6)
    if not all(abs((b[0] - a[0]) / fps - (b[1] - a[1])) < 1e-5
               for a, b in zip(native, native[1:])):
        raise ValueError("Frame/time cadence is inconsistent")
    result = []
    for player, rows in values.items():
        if len(rows) < 2:
            continue
        array = np.asarray(rows)
        frames, times = array[:, 0].astype(int), array[:, 1]
        segments = np.r_[0, np.cumsum(np.diff(frames) != 1)]
        result.append(Trajectory(game, player, team, frames, times, array[:, 2:], segments, fps))
    return result, {**excluded, "native_frames": len(native), "fps": fps}


def corrupt(trajectory, scenario, seed, config):
    """Fixed synthetic faults; never change reference coordinates or identities."""
    t = trajectory
    observed = t.xy.copy()
    keep = np.ones(len(t.frames), dtype=bool)
    fault = np.zeros(len(t.frames), dtype=bool)
    if scenario != "clean":
        rng = np.random.default_rng(np.random.SeedSequence([seed, t.game, t.track_id, 0]))
        noise = rng.normal(0, config["noise_sigma_m"], observed.shape)
        if scenario == "correlated_noise":
            correlation_s = config["noise_correlation_s"]
            if correlation_s <= 0:
                raise ValueError("Noise correlation time must be positive")
            for i in range(1, len(noise)):
                if t.segments[i] == t.segments[i - 1]:
                    rho = math.exp(-(t.times[i] - t.times[i - 1]) / correlation_s)
                    noise[i] = rho * noise[i - 1] + math.sqrt(1 - rho**2) * noise[i]
        observed += noise
    if scenario == "spikes":
        rng = np.random.default_rng(np.random.SeedSequence([seed, t.game, t.track_id, 1]))
        fault = rng.random(len(t.frames)) < config["spike_probability"]
        shift = np.where(t.xy < [52.5, 34], [10., 8.], [-10., -8.])
        observed[fault] += shift[fault]
    elif scenario == "gaps":
        for offset in (15, 30, 45):
            start = config["start_s"] + offset
            keep &= ~((t.times >= start) & (t.times < start + config["gap_duration_s"]))
    elif scenario == "relocation":
        start = config["start_s"] + 30
        fault = (t.times >= start) & (t.times < start + config["relocation_duration_s"])
        if fault.any():
            shift = np.where(t.xy[np.flatnonzero(fault)[0]] < [52.5, 34], [10., 8.], [-10., -8.])
            observed[fault] += shift
    elif scenario not in ("clean", "noise", "correlated_noise"):
        raise ValueError("Unknown benchmark scenario")
    on_pitch = np.isfinite(observed).all(axis=1) & (observed >= 0).all(axis=1) & (observed <= [105, 68]).all(axis=1)
    return observed, keep & on_pitch, fault, {"injected_missing": int((~keep).sum()),
                                             "off_pitch_after_noise": int((keep & ~on_pitch).sum())}


class AuditedMetrics(PitchMetrics):
    """Observe actual production metric intervals, compare equal reference paths."""
    def __init__(self, trajectory):
        super().__init__(trajectory.fps)
        self.reference = trajectory
        self.lookup = {int(frame): i for i, frame in enumerate(trajectory.frames)}
        step = np.linalg.norm(np.diff(trajectory.xy, axis=0), axis=1)
        step[np.diff(trajectory.segments) != 0] = 0
        self.path = np.r_[0., np.cumsum(step)]
        self.covered_distance = 0.
        self.speed_error_time = 0.

    def observe(self, segment, row):
        state = self.tracks.get((segment, row.track_id))
        previous = state["anchor"] if state is not None else None
        old_distance = state["distance_m"] if state is not None else 0.
        old_duration = state["duration_s"] if state is not None else 0.
        super().observe(segment, row)
        state = self.tracks[(segment, row.track_id)]
        dt = state["duration_s"] - old_duration
        if dt > 0:
            a, b = self.lookup[previous.frame], self.lookup[row.frame]
            if self.reference.segments[a] != self.reference.segments[b]:
                raise AssertionError("Metric interval crosses a native reference gap")
            target = self.path[b] - self.path[a]
            self.covered_distance += target
            estimated = state["distance_m"] - old_distance
            self.speed_error_time += abs(estimated - target) * 3.6

    def totals(self):
        return {"distance_m": sum(s["distance_m"] for s in self.tracks.values()),
                "duration_s": sum(s["duration_s"] for s in self.tracks.values()),
                "reference_covered_distance_m": self.covered_distance,
                "speed_error_time": self.speed_error_time,
                "rejected_steps": sum(s["rejected_steps"] for s in self.tracks.values())}


def evaluate_trajectory(t, scenario, seed, config):
    observed, keep, faults, missing = corrupt(t, scenario, seed, config)
    smoother = PitchSmoother()
    raw_metrics, filtered_metrics = AuditedMetrics(t), AuditedMetrics(t)
    raw_error = filtered_error = common_raw_error = 0.
    raw_count = filtered_count = accepted_faults = 0
    statuses = {}
    lag_sse = np.zeros(len(config["lag_grid_frames"]))
    lag_count = 0
    lookup = {int(frame): i for i, frame in enumerate(t.frames)}
    for i in range(len(t.frames)):
        time_s, frame, segment = float(t.times[i]), int(t.frames[i]), int(t.segments[i])
        smoother.advance(time_s)
        if not keep[i]:
            continue
        row = TrackingRow(frame=frame, time_s=time_s, track_id=t.track_id, team=t.team,
                          x_m=float(observed[i, 0]), y_m=float(observed[i, 1]))
        raw_metrics.observe(segment, row)
        error = float(np.square(observed[i] - t.xy[i]).sum())
        raw_error += error
        raw_count += 1
        filtered, broken, status = smoother.observe(segment, row)
        statuses[status] = statuses.get(status, 0) + 1
        if broken:
            filtered_metrics.break_chain(segment, t.track_id)
        if filtered is None:
            continue
        filtered_metrics.observe(segment, filtered)
        xy = np.array([filtered.x_m, filtered.y_m])
        filtered_error += float(np.square(xy - t.xy[i]).sum())
        common_raw_error += error
        filtered_count += 1
        accepted_faults += int(faults[i])
        delayed = [lookup.get(frame - lag) for lag in config["lag_grid_frames"]]
        if all(j is not None and t.segments[j] == segment for j in delayed):
            lag_sse += np.square(t.xy[delayed] - xy).sum(axis=1)
            lag_count += 1
    consecutive = np.diff(t.segments) == 0
    reference_distance = float(np.linalg.norm(np.diff(t.xy, axis=0), axis=1)[consecutive].sum())
    reference_duration = float(np.diff(t.times)[consecutive].sum())
    return {"game": t.game, "track_id": t.track_id, "team": t.team,
            "reference_count": len(t.frames), "reference_distance_m": reference_distance,
            "reference_duration_s": reference_duration, "raw_count": raw_count,
            "filtered_count": filtered_count, "raw_squared_error": raw_error,
            "filtered_squared_error": filtered_error, "common_raw_squared_error": common_raw_error,
            "injected_faults": int(faults.sum()), "accepted_faults": accepted_faults,
            "lag_sse": lag_sse.tolist(), "lag_count": lag_count, "statuses": statuses,
            "raw_metrics": raw_metrics.totals(), "filtered_metrics": filtered_metrics.totals(), **missing}


def summarize(results, fps, lag_grid):
    def total(key):
        return sum(r[key] for r in results)
    n, nr, nf = total("reference_count"), total("raw_count"), total("filtered_count")
    reference_distance, reference_duration = total("reference_distance_m"), total("reference_duration_s")
    summary = {"reference_count": n, "reference_distance_m": reference_distance,
               "reference_duration_s": reference_duration, "raw_count": nr, "filtered_count": nf,
               "raw_coverage": nr / n, "filtered_coverage": nf / n,
               "raw_position_rmse_m": math.sqrt(total("raw_squared_error") / nr) if nr else None,
               "raw_common_position_rmse_m": math.sqrt(total("common_raw_squared_error") / nf) if nf else None,
               "filtered_position_rmse_m": math.sqrt(total("filtered_squared_error") / nf) if nf else None,
               "injected_faults": total("injected_faults"), "accepted_faults": total("accepted_faults"),
               "injected_missing": total("injected_missing"),
               "off_pitch_after_noise": total("off_pitch_after_noise")}
    for mode in ("raw", "filtered"):
        metrics = {key: sum(r[f"{mode}_metrics"][key] for r in results)
                   for key in results[0][f"{mode}_metrics"]}
        distance, target, duration = metrics["distance_m"], metrics["reference_covered_distance_m"], metrics["duration_s"]
        summary[f"{mode}_motion"] = {
            **metrics, "represented_time_fraction": duration / reference_duration,
            "full_distance_relative_error": (distance - reference_distance) / reference_distance if reference_distance else None,
            "covered_distance_relative_error": (distance - target) / target if target else None,
            "speed_mae_kmh": metrics["speed_error_time"] / duration if duration else None}
    lag_sse = np.sum([r["lag_sse"] for r in results], axis=0)
    lag_count = total("lag_count")
    summary["apparent_lag_ms"] = lag_grid[int(np.argmin(lag_sse))] / fps * 1000 if lag_count else None
    summary["lag_comparison_count"] = lag_count
    summary["lag_rmse_m"] = np.sqrt(lag_sse / lag_count).tolist() if lag_count else []
    return summary


def run(data_dir, manifest_path, output):
    output = Path(output)
    if output.exists():
        raise ValueError("Output must be a new file")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    config = manifest["benchmark"]
    trajectories, sources = [], []
    for spec in manifest["files"]:
        path = Path(data_dir) / spec["filename"]
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != spec["sha256"]:
            raise ValueError(f"Source hash mismatch: {path.name}")
        rows, info = load_tracking(path, spec["game"], "A" if spec["team"] == "Home" else "B",
                                   config["start_s"], config["stop_s"], config["period"])
        trajectories.extend(rows)
        sources.append({**spec, **info})
    if not trajectories or len({t.fps for t in trajectories}) != 1:
        raise ValueError("Need nonempty trajectories with a common sampling rate")
    fps = trajectories[0].fps
    trials = []
    for game in sorted({t.game for t in trajectories}):
        for scenario in config["scenarios"]:
            seeds = config["seeds"][:1] if scenario == "clean" else config["seeds"]
            for seed in seeds:
                details = [evaluate_trajectory(t, scenario, seed, config) for t in trajectories if t.game == game]
                trials.append({"game": game, "scenario": scenario, "seed": seed,
                               "summary": summarize(details, fps, config["lag_grid_frames"]), "tracks": details})
                print(json.dumps({"game": game, "scenario": scenario, "seed": seed,
                                  "raw_rmse": trials[-1]["summary"]["raw_position_rmse_m"],
                                  "filtered_rmse": trials[-1]["summary"]["filtered_position_rmse_m"]}), flush=True)
    report = {"source": manifest["source"], "repository": manifest["repository"], "commit": manifest["commit"],
              "scope": "Reference-coordinate fault-injection benchmark only; not video tracking accuracy or absolute ground truth",
              "configuration": config, "fps": fps, "sources": sources,
              "filter": {key: getattr(PitchSmoother, key) for key in ("window_s", "max_gap_s", "min_span_s",
                         "noise_margin_m", "max_speed_kmh", "method",
                         "recovery_horizon_s", "acceleration_margin_m_s2")
                         if hasattr(PitchSmoother, key)}, "trials": trials}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("docs/fixtures/metrica_benchmark.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.data_dir, args.manifest, args.output)


if __name__ == "__main__":
    main()
