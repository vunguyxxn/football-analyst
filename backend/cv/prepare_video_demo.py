"""Copy verified local media/tracking for the frontend demo; no CV rerun."""
import argparse
import json
from pathlib import Path
import shutil
import re

from backend.cv.prepare_video_review import digest, workspace_path

ROOT = Path(__file__).resolve().parents[2]


def prepare_job(job_id, source, output, name):
    """Switch demo atomically, verifying new video/result identity, retaining old assets."""
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise ValueError("Invalid job ID")
    source, output = workspace_path(source), workspace_path(output)
    folder = ROOT / "data/processed/video_jobs" / job_id
    status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Demo job must be completed")
    uploaded = next(folder.glob("source.*"))
    if digest(source) != digest(uploaded):
        raise ValueError("Requested demo source does not match job video")
    result = status["result"]
    hashes = [digest(folder / f"chunk-{index}.json") for index in range(result["chunks"])]
    output.mkdir(parents=True, exist_ok=True)
    video_name = f"{job_id}.mp4"
    target = output / video_name
    if target.exists() and digest(target) != digest(source):
        raise ValueError("Existing demo video differs")
    if not target.exists():
        shutil.copyfile(source, target)
    manifest = {"version": 2, "kind": "processed_video_job", "job_id": job_id, "name": name,
                "video_sha256": digest(target), "video_file": video_name,
                "frames": result["frames"], "fps": result["fps"], "duration_s": result["duration_s"],
                "chunk_sha256": hashes,
                "note": "Source-matched image-space tracking. No pitch coordinates from an older clip."}
    previous = output / "manifest.json"
    if previous.exists():
        backup = output / f"manifest-backup-{digest(previous)[:16]}.json"
        if not backup.exists():
            shutil.copyfile(previous, backup)
    temporary = output / f"manifest-{job_id}.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(previous)
    return manifest


def prepare(output):
    output = workspace_path(output)
    if output.exists():
        raise FileExistsError("Use a new output directory")
    plan = json.loads((ROOT / "docs/fixtures/video_review_plan.json").read_text())
    raw = workspace_path(plan["raw_video"])
    if digest(raw) != plan["raw_sha256"]:
        raise ValueError("Raw video changed; do not pair tracking with another clip")
    tracking = ROOT / "data/processed/clip_11f23eea/pitch_smoothing_v3_check/tracking.jsonl"
    # Match the frozen, audited v3 keys and source, not an arbitrary file.
    samples = json.loads((ROOT / "docs/fixtures/vid1_11f23eea_prediction_samples.json").read_text())
    if samples["source_sha256"] != plan["video_sha256"]:
        raise ValueError("Frozen tracking source differs")
    if digest(tracking) != samples["audit"]["input_sha256"]["filtered"]:
        raise ValueError("V3 tracking differs from the frozen, audited artifact")
    rows = [json.loads(line) for line in tracking.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 4735 or len({(r["frame"], r["track_id"]) for r in rows}) != len(rows):
        raise ValueError("Unexpected v3 tracking keys/count")
    for row in rows:
        if set(row) != {"frame", "time_s", "track_id", "team", "x_m", "y_m"}:
            raise ValueError("TrackingRow fields differ")
    output.mkdir(parents=True)
    shutil.copyfile(raw, output / "video.mp4")
    shutil.copyfile(tracking, output / "tracking.jsonl")
    manifest = {"version": 1, "offset_seconds": plan["raw_frame_offset"] / plan["fps"],
                "video_sha256": digest(output / "video.mp4"), "tracking_sha256": digest(output / "tracking.jsonl"),
                "rows": len(rows), "note": "Original H.264 clip with +10s mapping to the processed clean clip; provisional coordinates only"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("frontend/public/video-demo"))
    parser.add_argument("--job-id")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--name", default="Clip mẫu đã xử lý")
    args = parser.parse_args()
    if args.job_id:
        if not args.source:
            parser.error("--source is required with --job-id")
        print(json.dumps(prepare_job(args.job_id, args.source, args.output, args.name), ensure_ascii=False))
    else:
        prepare(args.output)
