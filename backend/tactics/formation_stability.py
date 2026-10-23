"""Temporal diagnostic only: consensus cannot establish tactical correctness."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from backend.cv.metrica_benchmark import load_tracking
from backend.tactics.formation import analyze_window, spatial_shape
from backend.tactics.formation_templates import POLICY, template_shape
from backend.tactics.formation_aligned import POLICY as ALIGNED_POLICY, aligned_shape


OFFSETS_S = (1., 3., 5., 7., 9.)
MAX_OFFSET_ERROR_S = .08
MINIMUM_AGREEMENT = 4


def assess_stability(median, samples):
    """Never promote an unknown median or count only the emitted snapshots."""
    if len(samples) != 5:
        raise ValueError("Need five scheduled slots")
    if median["status"] != "observed_shape":
        return {"status": "unknown", "reason": "median_unknown"}
    if any(s is None for s in samples):
        return {"status": "unknown", "reason": "missing_temporal_slot"}
    counts = Counter(s.get("shape") if s["status"] == "observed_shape" else "unknown" for s in samples)
    agreeing = counts[median["shape"]]
    base = {"agreement_count": agreeing, "scheduled_samples": 5,
            "sample_label_counts": dict(counts)}
    if agreeing < MINIMUM_AGREEMENT:
        return {**base, "status": "unknown", "reason": "insufficient_temporal_support"}
    return {**base, "status": "temporally_supported", "shape": median["shape"]}


def check_window(trajectories, start_s, stop_s, goalkeeper_id, direction, *, include_aligned=False):
    if abs(stop_s - start_s - 10) > 1e-9:
        raise ValueError("Protocol requires ten-second windows")
    methods = ("gap", "template", "aligned") if include_aligned else ("gap", "template")
    median = {m: analyze_window(trajectories, start_s, stop_s, goalkeeper_id, direction, method=m)
              for m in methods}
    base = {"start_s": start_s, "stop_s": stop_s, "median": median, "samples": []}
    if "players" not in median["gap"]:
        base["temporal"] = {m: {"status": "unknown", "reason": "window_quality_rejected"} for m in median}
        return base
    active = []
    for t in trajectories:
        rows = {int(f): (float(time), xy.tolist()) for f, time, xy in zip(t.frames, t.times, t.xy)
                if start_s <= time < stop_s}
        if rows:
            active.append((t.track_id, rows))
    common = sorted(set.intersection(*(set(rows) for _, rows in active)))
    times = {f: active[0][1][f][0] for f in common}
    used = set()
    for offset in OFFSETS_S:
        target = start_s + offset
        frame = min(common, key=lambda f: (abs(times[f] - target), f))
        slot = {"target_s": target, "observed": False}
        if frame not in used and abs(times[frame] - target) <= MAX_OFFSET_ERROR_S + 1e-9:
            used.add(frame)
            points = {p: rows[frame][1] for p, rows in active}
            slot.update(observed=True, frame=frame, time_s=times[frame], positions=points,
                        gap=spatial_shape(points, goalkeeper_id, direction),
                        template=template_shape(points, goalkeeper_id, direction))
            if include_aligned:
                slot["aligned"] = aligned_shape(points, goalkeeper_id, direction)
        base["samples"].append(slot)
    base["temporal"] = {m: assess_stability(median[m], [slot.get(m) for slot in base["samples"]])
                        for m in median}
    return base


def run(root, output, *, include_aligned=False):
    if output.exists():
        raise FileExistsError(output)
    protocol_path = root / "docs/fixtures/formation_stability_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    # Fail closed if someone edits the fixture without updating the implementation.
    if (protocol["sample_offsets_s"] != list(OFFSETS_S) or protocol["maximum_sample_offset_error_s"] != MAX_OFFSET_ERROR_S or protocol["minimum_agreeing_samples"] != MINIMUM_AGREEMENT or protocol["window_s"] != 10 or protocol["minimum_joint_coverage"] != .8 or protocol["require_all_five_observed_slots"] is not True):
        raise ValueError("Protocol and implementation disagree")
    if not isinstance(protocol["start_s"], int) or not isinstance(protocol["stop_s"], int) or protocol["start_s"] < 0 or protocol["stop_s"] <= protocol["start_s"] or (protocol["stop_s"] - protocol["start_s"]) % 10:
        raise ValueError("Protocol requires complete ten-second windows")
    manifest = json.loads((root / protocol["source_manifest"]).read_text(encoding="utf-8"))
    windows, sources = [], []
    for team in protocol["teams"]:
        filename = f"Sample_Game_{team['game']}_RawTrackingData_{team['side']}_Team.csv"
        source = root / "data/raw/metrica" / filename
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        expected = next(s["sha256"] for s in manifest["files"] if s["filename"] == filename)
        if digest != expected:
            raise ValueError(f"Source hash mismatch: {filename}")
        tracks, audit = load_tracking(source, team["game"], team["team"], protocol["start_s"],
                                      protocol["stop_s"], protocol["period"])
        sources.append({**team, "path": source.relative_to(root).as_posix(), "sha256": digest, "loader_audit": audit})
        for start in range(protocol["start_s"], protocol["stop_s"], protocol["window_s"]):
            result = check_window(tracks, start, start + protocol["window_s"], team["goalkeeper_id"], team["attack_direction"], include_aligned=include_aligned)
            windows.append({"game": team["game"], "team": team["team"], "period": protocol["period"], **result})
    summary = {m: {"median_emitted": sum(w["median"][m]["status"] == "observed_shape" for w in windows),
                   "temporally_supported": sum(w["temporal"][m]["status"] == "temporally_supported" for w in windows),
                   "reasons": dict(Counter(w["temporal"][m].get("reason", "supported") for w in windows))}
               for m in (("gap", "template", "aligned") if include_aligned else ("gap", "template"))}
    result = {"kind": "formation_stability_v1", "has_reference_labels": False,
              "protocol": protocol, "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              "template_policy": POLICY, "sources": sources, "total_windows": len(windows),
              "summary": summary, "windows": windows,
              "warning": "Temporal agreement is not tactical accuracy; no detector/default/threshold change"}
    if include_aligned:
        result["aligned_policy"] = ALIGNED_POLICY
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-aligned", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if not output.is_relative_to(root) or output.exists():
        parser.error("Output must be a new file inside project")
    report = run(root, output, include_aligned=args.include_aligned)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
