"""Source-bound agent review, separate from unmodified tracking and learned models."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROLES = {"red_outfield", "white_outfield", "referee", "goalkeeper", "uncertain"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_context(context, fps, total):
    if context.get("kind") != "video_context_development_review_v1" or context.get("independently_validated") is not False:
        raise ValueError("Only provisional context reviews supported")
    if set(context["team_labels"]) != {"A", "B"}:
        raise ValueError("Need two group labels")
    seen = set()
    for rule in context["role_tracks"]:
        start, end, ident = rule["start_frame"], rule["end_frame"], rule["id"]
        if (any(type(v) is not int for v in (start, end, ident)) or not 0 <= start < end <= total
                or ident < 0 or ident in seen or rule["role"] not in ("referee", "goalkeeper")
                or len(set(rule["review_frames"])) < 2
                or any(type(f) is not int or not start <= f < end for f in rule["review_frames"])
                or min(rule["review_frames"]) != start or max(rule["review_frames"]) != end-1):
            raise ValueError("Invalid or overlapping reviewed role track")
        seen.add(ident)
    for name in ("directions", "window_notes"):
        previous = 0.
        for interval in context[name]:
            start, end = interval["start_s"], interval["end_s"]
            if (not all(type(v) in (int, float) and math.isfinite(v) for v in (start, end))
                    or not previous <= start < end <= total/fps):
                raise ValueError("Invalid review scope")
            previous = end
            if name == "directions" and any(type(interval[g]) is not int or interval[g] not in (-1, 1) for g in ("A", "B")):
                raise ValueError("Direction must be +1 or -1")


def role_for(row, context):
    return next((rule["role"] for rule in context["role_tracks"]
                 if rule["id"] == row["track_id"] and rule["start_frame"] <= row["frame"] < rule["end_frame"]), None)


def window_context(context, segment, group):
    direction = next((item[group] for item in context["directions"]
                      if item["start_s"] <= segment["start_s"] < segment["end_s"] <= item["end_s"]), None)
    note = next((item for item in context["window_notes"]
                 if item["start_s"] <= segment["start_s"] < segment["end_s"] <= item["end_s"]), None)
    return {"team_label": context["team_labels"][group], "attack_direction": direction,
            "direction_status": "agent_inferred_not_independent" if direction else "unknown",
            "note": note["note"] if note else None, "review_times_s": [frame/context["fps"] for frame in note["frames"]] if note else []}


def prepare(job, labels, output):
    job, labels, output = [Path(path).resolve() for path in (job, labels, output)]
    if any(not path.is_relative_to(ROOT) for path in (job, labels, output)) or output.exists():
        raise ValueError("Use workspace paths and new output")
    status = json.loads((job/"status.json").read_text(encoding="utf-8"))
    result = status["result"]
    review = json.loads(labels.read_text(encoding="utf-8"))
    if any(key in review for key in ("fps", "frames_total", "labels_path", "input_sha256", "audit")):
        raise ValueError("Annotation cannot overwrite derived audit fields")
    if (status["status"] != "completed" or review["person_job_id"] != job.name
            or review["source_sha256"] != digest(next(job.glob("source.*")))):
        raise ValueError("Context source/job mismatch")
    validate_context(review, result["fps"], result["frames"])
    records, hashes, appearances = {}, [], {}
    wanted = set(review["frames"]) | {frame for rule in review["role_tracks"] for frame in rule["review_frames"]}
    role_ids = {rule["id"] for rule in review["role_tracks"]}
    for index in range(result["chunks"]):
        path = job/f"chunk-{index}.json"
        hashes.append(digest(path))
        for record in json.loads(path.read_text(encoding="utf-8"))["frames"]:
            for box in record["boxes"]:
                key = record["frame"], box["id"]
                if key in records:
                    raise ValueError("Duplicate detection")
                if record["frame"] in wanted:
                    records[key] = box
                if box["id"] in role_ids:
                    appearances.setdefault(box["id"], []).append(record["frame"])
    expected = {key for key in records if key[0] in review["frames"]}
    seen, confusion = set(), Counter()
    for label in review["labels"]:
        key = label["frame"], label["id"]
        if key in seen or key not in expected or label["role"] not in ROLES or label["xyxy"] != records[key]["xyxy"]:
            raise ValueError("Duplicate, missing or mismatched visual label")
        seen.add(key)
        confusion[label["role"], records[key]["group"]] += 1
    if seen != expected:
        raise ValueError("Review must cover every detector-selected crop at scheduled frames")
    for rule in review["role_tracks"]:
        frames = appearances.get(rule["id"], [])
        if (not frames or min(frames) != rule["start_frame"] or max(frames)+1 != rule["end_frame"]
                or any((frame, rule["id"]) not in records for frame in rule["review_frames"])):
            raise ValueError("Reviewed role track differs from detections")
        for label in review["labels"]:
            if label["id"] == rule["id"] and rule["start_frame"] <= label["frame"] < rule["end_frame"] and label["role"] != rule["role"]:
                raise ValueError("Conflicting manual roles")
    outfield = sum(count for (role, _), count in confusion.items() if role.endswith("outfield"))
    correct = confusion["red_outfield", "A"] + confusion["white_outfield", "B"]
    payload = {**review, "fps": result["fps"], "frames_total": result["frames"], "labels_path": labels.relative_to(ROOT).as_posix(),
               "input_sha256": {"labels": digest(labels), "chunks": hashes,
                                "positions": digest(job/"pitch_estimate/tracking.jsonl")},
               "audit": {"sampled_people": len(seen), "outfield_people": outfield, "correct_outfield_group": correct,
                         "outfield_unknown": confusion["red_outfield", "unknown"]+confusion["white_outfield", "unknown"],
                         "referee_samples": sum(c for (r, _), c in confusion.items() if r == "referee"),
                         "referee_in_team_groups": confusion["referee", "A"]+confusion["referee", "B"],
                         "goalkeeper_samples": sum(c for (r, _), c in confusion.items() if r == "goalkeeper"),
                         "goalkeeper_in_team_groups": confusion["goalkeeper", "A"]+confusion["goalkeeper", "B"],
                         "confusion": [{"role": r, "group": g, "count": c} for (r, g), c in sorted(confusion.items()) if c]}}
    output.mkdir(parents=True)
    (output/"report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return payload


def load_context(job, result):
    path = job/"tactical_context/report.json"
    if not path.is_file():
        return None
    context = json.loads(path.read_text(encoding="utf-8"))
    validate_context(context, result["fps"], result["frames"])
    inputs = context["input_sha256"]
    labels = (ROOT/context["labels_path"]).resolve()
    if not labels.is_relative_to(ROOT) or digest(labels) != inputs["labels"]:
        raise ValueError("Context annotation changed or left workspace")
    original = json.loads(labels.read_text(encoding="utf-8"))
    if any(context.get(key) != value for key, value in original.items()):
        raise ValueError("Context differs from visual annotations")
    if (context["source_sha256"] != result["source_sha256"] or context["person_job_id"] != job.name
            or context["fps"] != result["fps"] or context["frames_total"] != result["frames"]
            or inputs["positions"] != digest(job/"pitch_estimate/tracking.jsonl")
            or inputs["chunks"] != [digest(job/f"chunk-{i}.json") for i in range(result["chunks"])]):
        raise ValueError("Stale context review/source/positions/detections")
    return context


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("job", "labels", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.job, args.labels, args.output)["audit"]))
