"""Offline cross-clip upload evaluation; no calibration fitting or job mutations."""
import argparse
from collections import Counter
import json
from pathlib import Path

from backend.cv.audit_pitch_result import audit
from backend.cv.evaluate_video_review import evaluate_frame
from backend.cv.job_pitch_analysis import digest, pitch_folder, read_json
from backend.cv.tracking_summary import summarize


def sparse_review(folder, labels, gate):
    samples = {sample["frame"]: sample for sample in labels["frames"]}
    info = read_json(folder / "status.json")["result"]
    predictions = {}
    for i in range(info["chunks"]):
        for record in read_json(folder / f"chunk-{i}.json")["frames"]:
            if record["frame"] in samples:
                predictions[record["frame"]] = [{"track_id": box["id"], "team": box["group"],
                    "image_xy": [(box["xyxy"][0]+box["xyxy"][2])/2, box["xyxy"][3]]} for box in record["boxes"]]
    if set(predictions) != set(samples):
        raise ValueError("Missing sample frames in job")
    frames = []
    for frame, sample in sorted(samples.items()):
        refs = [{"identity": p["identity"], "team": p["role"], "xy": p["xy"], "visibility": "visible"} for p in sample["people"]]
        if len({p["identity"] for p in refs}) != len(refs):
            raise ValueError("Duplicate visual identity")
        frames.append({"frame": frame, **evaluate_frame(refs, predictions[frame], gate)})
    first = [m for m in frames[0]["matches"] if not m["ambiguous"] and m["label_team"] in ("white", "opponent")]
    # A/B are arbitrary colour clusters. Resolve the permutation on the FIRST
    # sample only, then evaluate roles on later samples without remapping.
    scores = {white: sum(m["predicted_team"] == (white if m["label_team"] == "white" else other) for m in first)
              for white, other in (("A", "B"), ("B", "A"))}
    white = max(scores, key=scores.get)
    mapping = {"white": white, "opponent": "B" if white == "A" else "A"} if scores[white] > min(scores.values()) else None
    matches = [m for f in frames for m in f["matches"] if not m["ambiguous"]]
    roles = Counter(f"{m['label_team']}->{m['predicted_team']}" for m in matches)
    checks = [m for f in frames[1:] for m in f["matches"] if not m["ambiguous"] and m["label_team"] in ("white", "opponent")]
    pairs, changes, disappearances = 0, [], []
    for before, after in zip(frames, frames[1:]):
        if after["frame"]-before["frame"] > 15:
            continue
        a = {m["identity"]: m for m in before["matches"] if not m["ambiguous"] and m["label_team"] in ("white", "opponent")}
        b = {m["identity"]: m for m in after["matches"] if not m["ambiguous"] and m["label_team"] in ("white", "opponent")}
        pairs += len(a.keys() & b.keys())
        changes.extend({"identity": ident, "from": a[ident]["track_id"], "to": b[ident]["track_id"]}
                       for ident in a.keys() & b.keys() if a[ident]["track_id"] != b[ident]["track_id"])
        disappearances.extend(sorted(a.keys()-b.keys()))
    positive = sum(p["role"] in ("white", "opponent") for s in samples.values() for p in s["people"])
    return {"gate_px": gate, "outfield_labels": positive,
            "outfield_matched": sum(m["label_team"] in ("white", "opponent") for m in matches),
            "first_sample_colour_mapping": mapping, "heldout_sample_role_matches": len(checks),
            "heldout_sample_role_correct": sum(m["predicted_team"] == mapping[m["label_team"]] for m in checks) if mapping else None,
            "role_pairs": dict(roles), "sampled_identity_pairs": pairs,
            "apparent_sampled_id_changes": changes, "sample_disappearances": disappearances,
            "referee_in_team_groups": sum(m["label_team"] == "referee" and m["predicted_team"] in ("A", "B") for m in matches),
            "outside_people_kept": sum(m["label_team"] == "outside" for m in matches), "frames": frames}


def evaluate_job(folder, clip, labels, gates):
    folder = Path(folder)
    status = read_json(folder / "status.json")
    if status["status"] != "completed":
        raise ValueError("Evaluate completed jobs only")
    info = status["result"]
    source = folder / "source.mp4"
    if digest(source) != clip["source_sha256"] or labels["source_sha256"] != clip["source_sha256"]:
        raise ValueError("Clip, job and visual labels must have matching source hashes")
    if any(info[key] != clip["info"][key] for key in ("frames", "fps", "width", "height")):
        raise ValueError("Manifest/job metadata mismatch")
    if info.get("source_sha256", clip["source_sha256"]) != clip["source_sha256"]:
        raise ValueError("Job source hash mismatch")
    summary = summarize(folder, info)
    selected = pitch_folder(folder)
    reference = {"source_sha256": clip["source_sha256"], "max_error_m": 1., "checkpoints": clip.get("checkpoints", [])}
    pitch_audit = audit(selected, source, info["fps"], reference) if (selected / "report.json").is_file() else None
    tactics = read_json(selected / "tactics.json") if (selected / "tactics.json").is_file() else {"windows": []}
    trace_errors = []
    for window in tactics["windows"]:
        if window["status"] != "observed_cluster":
            if window.get("recommendations"):
                trace_errors.append("Advice without a supported observed cluster")
            continue
        metrics = window["metrics"]
        for advice in window["recommendations"]:
            if not advice.get("condition") or not advice.get("evidence"):
                trace_errors.append("Advice missing condition/evidence")
            for evidence in advice.get("evidence", []):
                value = metrics.get(evidence["metric"])
                if "index" in evidence and value is not None:
                    value = value[evidence["index"]]
                if value != evidence["value"]:
                    trace_errors.append("Advice value disagrees with window metric")
    return {"name": clip["name"], "source_sha256": clip["source_sha256"], "job_id": folder.name,
            "duration_s": info["frames"]/info["fps"], "tracking": summary,
            "boundary_filter": info.get("boundary_filter"), "calibration": read_json(folder / "calibration-status.json"),
            "pitch_audit": pitch_audit, "calibrated_seconds": pitch_audit["calibrated_seconds"] if pitch_audit else 0,
            "tactical_windows": sum(w["status"] == "observed_cluster" for w in tactics["windows"]),
            "recommendation_items": sum(len(w.get("recommendations", [])) for w in tactics["windows"]),
            "tactics_trace_errors": trace_errors,
            "sparse_reviews": [sparse_review(folder, labels, gate) for gate in gates]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--jobs", required=True, type=Path, help="JSON mapping clip names to job folders")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for path in (args.manifest, args.labels, args.jobs, args.output):
        if not path.resolve().is_relative_to(root):
            parser.error("All paths must be inside the workspace")
    if args.output.exists():
        parser.error("Use a new report file")
    manifest, labels, jobs = map(read_json, (args.manifest, args.labels, args.jobs))
    for value in jobs.values():
        if not Path(value).resolve().is_relative_to(root):
            parser.error("Job folders must be inside the workspace")
    by_name = {c["name"]: c for c in labels["clips"]}
    result = {"scope": "full upload smoke test and sparse agent visual review; not independent accuracy, recall, IDF1 or tactical validation",
              "input_hashes": {"manifest": digest(args.manifest), "labels": digest(args.labels)},
              "clips": [evaluate_job(jobs[c["name"]], c, by_name[c["name"]], labels["sensitivity_gates_px"]) for c in manifest["clips"]]}
    result["automatic_analysis_ready_clips"] = sum(c["calibrated_seconds"] > 0 and c["tactical_windows"] > 0 for c in result["clips"])
    result["evaluation_status"] = "completed"  # Completion is not product acceptance.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps([{k: c[k] for k in ("name", "calibrated_seconds", "tactical_windows", "tactics_trace_errors")} for c in result["clips"]], ensure_ascii=False))
    return 1 if any(c["tactics_trace_errors"] or c["pitch_audit"] and c["pitch_audit"]["status"] == "needs_review" for c in result["clips"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
