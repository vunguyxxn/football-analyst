"""Offline checks of immutable upload results; never refit or publish coordinates."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import numpy as np

from backend.cv.job_pitch_analysis import digest, read_json
from backend.cv.pitch_keypoints import check_landmarks


def audit(result_dir, source, fps, reference):
    result_dir, source = Path(result_dir), Path(source)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be positive")
    report = read_json(result_dir / "report.json")
    source_hash = digest(source)
    if source_hash != report["source_sha256"] or source_hash != reference["source_sha256"]:
        raise ValueError("Reference, source and result hashes must match")
    publication = report["publication"]
    for filename, key in (("tracking.jsonl", "tracking_sha256"), ("geometry.jsonl", "geometry_sha256")):
        if digest(result_dir / filename) != publication[key]:
            raise ValueError(f"Artifact changed: {filename}")
    segments = [(round(s["start_s"]*fps), round(s["end_s"]*fps), s["segment"]) for s in report["segments"]]
    errors, frames, counts, previous = [], set(), Counter(), {}
    bins = defaultdict(lambda: np.zeros((14, 21)))
    rows = 0
    with (result_dir / "tracking.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            f, x, y = row["frame"], row["x_m"], row["y_m"]
            owners = [segment for start, end, segment in segments if start <= f < end]
            if len(owners) != 1:
                errors.append(f"frame {f}: missing/overlapping calibrated segment")
                continue
            key = (owners[0], row["track_id"])
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= 105 and 0 <= y <= 68):
                errors.append(f"frame {f}: outside pitch")
                continue
            if abs(row["time_s"] - f/fps) > 1e-6:
                errors.append(f"frame {f}: timestamp mismatch")
            if f <= previous.get(key, -1):
                errors.append(f"frame {f}: duplicate/unordered track")
            previous[key] = f
            counts[key] += 1
            bins[key][min(13, int(y/68*14)), min(20, int(x/105*21))] += 1/fps
            frames.add(f)
            rows += 1
    groups = {g["group"]: np.zeros((14, 21)) for g in report["groups"]}
    seen = set()
    for player in report["players"]:
        key = (player["segment"], player["id"])
        if key in seen or key not in counts:
            errors.append(f"{key}: duplicate/missing track")
        seen.add(key)
        heatmap = np.asarray(player["heatmap_seconds"])
        if heatmap.shape != (14, 21) or not np.allclose(heatmap, bins[key], atol=1e-8, rtol=0):
            errors.append(f"{key}: heatmap disagrees with published positions")
        groups[player["group"]] += heatmap
        distance, duration = player["distance_m"], player["motion_s"]
        start, end, _ = next(s for s in segments if s[2] == key[0])
        if (not math.isfinite(distance) or distance < 0 or not 0 <= duration <= (end-start)/fps+1e-6
                or distance > duration*40/3.6+1e-6):
            errors.append(f"{key}: invalid observed motion")
        speed = player["maximum_speed_kmh"]
        if speed is not None and not 0 <= speed <= 40:
            errors.append(f"{key}: implausible speed")
        mean = player["mean_speed_kmh"]
        if duration and (mean is None or abs(mean-distance/duration*3.6) > 1e-6):
            errors.append(f"{key}: inconsistent mean speed")
    if seen != set(counts):
        errors.append("player list disagrees with position tracks")
    for group in report["groups"]:
        if not np.allclose(group["heatmap_seconds"], groups[group["group"]], atol=1e-8, rtol=0):
            errors.append(f"{group['group']}: team heatmap disagrees with player heatmaps")
    if rows != report["accepted_positions"] or len(frames) != report["frames_with_positions"]:
        errors.append("position/frame counts disagree")
    # Include historical rejected references if the new result covers them.
    checkpoints = {c["frame"]: c for c in reference["checkpoints"] + reference.get("excluded_checkpoints", [])}
    matrices = {}
    with (result_dir / "geometry.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            sample = json.loads(line)
            if sample["frame"] in checkpoints and sample["frame"] in frames:
                matrices[sample["frame"]] = sample["matrix"]
    checks = []
    for f, checkpoint in sorted(checkpoints.items()):
        evaluation = check_landmarks(matrices[f], checkpoint, reference["max_error_m"]) if f in matrices else {"status": "not_evaluable"}
        checks.append({"frame": f, **evaluation})
    failed = sum(c["status"] == "failed" for c in checks)
    return {"source_sha256": source_hash, "result_version": result_dir.name,
            "scope": "internal consistency and previously labelled development landmarks; not independent ground truth",
            "status": "needs_review" if errors or failed else "checks_passed" if matrices else "insufficient_landmark_evidence",
            "consistency_errors": errors, "positions": rows, "frames_with_positions": len(frames),
            "duration_s": report["duration_s"], "calibrated_seconds": sum((end-start)/fps for start, end, _ in segments),
            "position_frame_seconds": len(frames)/fps,
            "heatmap_person_seconds": rows/fps, "landmark_checks": checks,
            "landmark_counts": dict(Counter(c["status"] for c in checks)),
            "limits": ["Landmarks were selected during development by the same agent; not a blind accuracy test.",
                       "Distance checks establish consistency and speed bounds, not independently measured running distance.",
                       "105x68m is assumed. Unseen players and missing time are not reconstructed."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--fps", required=True, type=float)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if any(not p.resolve().is_relative_to(root) for p in (args.result_dir, args.source, args.reference, args.output)):
        parser.error("All paths must be inside the workspace")
    if args.output.exists():
        parser.error("Use a new output file to preserve previous audits")
    result = audit(args.result_dir, args.source, args.fps, read_json(args.reference))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "calibrated_seconds", "landmark_counts", "consistency_errors")}, ensure_ascii=False))
    return 1 if result["status"] == "needs_review" else 0


if __name__ == "__main__":
    raise SystemExit(main())
