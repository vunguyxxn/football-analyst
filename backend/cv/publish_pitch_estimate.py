"""Install a checked local pitch estimate, retaining the previous version for rollback."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
from uuid import uuid4

from backend.common.schemas import TrackingRow

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def publish(job, candidate, calibration, checks):
    job, candidate, calibration, checks = [Path(path).resolve() for path in (job, candidate, calibration, checks)]
    target = job / "pitch_estimate"
    if any(not path.is_relative_to(ROOT) for path in (job, candidate, calibration, checks)) or candidate == target or candidate.is_relative_to(target):
        raise ValueError("Use separate candidate and workspace paths")
    status = json.loads((job / "status.json").read_text(encoding="utf-8"))
    report = json.loads((candidate / "report.json").read_text(encoding="utf-8"))
    source = next(job.glob("source.*"))
    inputs = {"calibration": digest(calibration), "landmark_checks": digest(checks)}
    if (status["status"] != "completed" or report["kind"] != "uploaded_pitch_estimate_v1"
            or report["source_sha256"] != digest(source) or report["person_job_id"] != job.name
            or report["input_sha256"] != inputs or report["pitch_m"] != [105, 68] or report["origin"] != "bottom_left"
            or not report["landmark_checks"]["enabled"] or report["landmark_checks"]["independently_validated"] is not False):
        raise ValueError("Candidate/source/inputs differ or checks absent")
    fps, total = status["result"]["fps"], status["result"]["frames"]
    protocol = json.loads(checks.read_text(encoding="utf-8"))
    controls = json.loads(calibration.read_text(encoding="utf-8"))
    if (not math.isfinite(fps) or fps <= 0 or total <= 0
            or abs(report["duration_s"]-total/fps) > 1e-8
            or any(p["source_sha256"] != report["source_sha256"] for p in (controls, protocol))):
        raise ValueError("Clip timing or fixture source differs")
    expected_segments = [{"segment": i, "start_s": a["frame"]/fps,
                          "end_s": a.get("end_frame", min(total, a["frame"]+300))/fps}
                         for i, a in enumerate(controls["anchors"])]
    if report["segments"] != expected_segments:
        raise ValueError("Segments differ from calibration")
    scheduled = {c["frame"]: c for c in protocol["checkpoints"]}
    verified = {}
    failed = []
    for check in report["landmark_checks"]["results"]:
        frame = check["frame"]
        if check["status"] == "verified":
            errors = check["errors_m"]
            if (frame in verified or frame not in scheduled or len(errors) != len(scheduled[frame]["image_points"])
                    or not all(type(error) in (int, float) and math.isfinite(error) and 0 <= error <= protocol["max_error_m"] for error in errors)
                    or check["limit_m"] != protocol["max_error_m"] or check["max_error_m"] != max(errors)):
                raise ValueError("Invalid successful checkpoint")
            verified[frame] = check
        else:
            failed.append(frame)
    ranges, previous = [], 0
    for interval in report["calibrated_intervals"]:
        start, end = (round(interval[key]*fps) for key in ("start_s", "end_s"))
        if (not previous <= start < end <= total or start not in verified or end-1 not in verified
                or any(start <= frame < end for frame in failed)
                or not any(s["start_s"] <= start/fps < end/fps <= s["end_s"] for s in expected_segments)):
            raise ValueError("Published interval needs passing opening and closing checks within one anchor")
        checkpoints = sorted(frame for frame in verified if start <= frame < end)
        if any(frame not in verified for frame in scheduled if start <= frame < end):
            raise ValueError("Scheduled checkpoint missing inside interval")
        if any(b-a > protocol["max_gap_frames"] for a, b in zip(checkpoints, checkpoints[1:])):
            raise ValueError("Checkpoint spacing exceeded")
        ranges.append((start, end))
        previous = end
    if not ranges:
        raise ValueError("No checked interval to publish")
    path = candidate / "tracking.jsonl"
    if path.stat().st_size > 20*1024*1024:
        raise ValueError("Tracking exceeds API limit")
    keys, frames = set(), set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = TrackingRow.model_validate_json(line)
            key = (row.frame, row.track_id)
            if (key in keys or not 0 <= row.x_m <= 105 or not 0 <= row.y_m <= 68
                    or not math.isfinite(row.time_s) or abs(row.time_s-row.frame/fps) > 1e-5
                    or not any(start <= row.frame < end for start, end in ranges)):
                raise ValueError("Tracking row outside checked intervals or invalid")
            keys.add(key)
            frames.add(row.frame)
            if len(keys) > 200000:
                raise ValueError("Too many rows")
    if not keys or len(keys) != report["accepted_positions"] or len(frames) != report["frames_with_positions"]:
        raise ValueError("Tracking counts differ")
    # Validate everything before mutating the currently displayed result.
    report["publication"] = {"policy": "opening_and_closing_landmark_checks_v1",
                             "inputs_sha256": inputs, "tracking_sha256": digest(path),
                             "independently_validated": False}
    stage = job / f"pitch-estimate-stage-{uuid4().hex}"
    stage.mkdir()
    shutil.copyfile(path, stage / "tracking.jsonl")
    (stage / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    backup = None
    if target.exists():
        backup = job / f"pitch-estimate-backup-{uuid4().hex}"
        target.rename(backup)
    try:
        stage.rename(target)
    except OSError:
        if backup is not None:
            backup.rename(target)
        raise
    return {"installed": str(target), "backup": str(backup) if backup else None,
            "positions": len(keys), "frames": len(frames), "intervals": report["calibrated_intervals"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("job", "candidate", "calibration", "checks"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.job, args.candidate, args.calibration, args.checks)))
