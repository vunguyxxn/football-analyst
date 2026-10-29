"""Source-locked development audit of ball points and event timing, not acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def in_windows(start, end, windows):
    return any(left <= start <= end < right for left, right in windows)


def scores(tp, fp, fn):
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def match_events(predictions, references, start_tolerance, end_tolerance):
    """Maximum-cardinality one-to-one matching; a duplicate cannot score twice."""
    graph = []
    for predicted in predictions:
        eligible = [i for i, reference in enumerate(references)
                    if predicted.get("group") == reference.get("group")
                    and abs(predicted["start_s"] - reference["start_s"]) <= start_tolerance
                    and abs(predicted["end_s"] - reference["end_s"]) <= end_tolerance]
        graph.append(sorted(eligible, key=lambda i: abs(predicted["start_s"] - references[i]["start_s"])
                           + abs(predicted["end_s"] - references[i]["end_s"])))
    assigned = {}

    def augment(index, seen):
        for reference in graph[index]:
            if reference in seen:
                continue
            seen.add(reference)
            if reference not in assigned or augment(assigned[reference], seen):
                assigned[reference] = index
                return True
        return False

    for index in range(len(predictions)):
        augment(index, set())
    return [{"prediction_index": prediction, "reference_id": references[reference]["id"]}
            for reference, prediction in sorted(assigned.items())]


def evaluate(folder, protocol, review):
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    if (report["source_sha256"] != protocol["source_sha256"] or review["source_sha256"] != protocol["source_sha256"]
            or report["person_job_id"] != protocol["person_job_id"] or report["frames"] != protocol["frames"]):
        raise ValueError("Source/job/frame identity differs")
    width, height = protocol["image_size"]
    count, fps = protocol["frames"], protocol["fps"]
    radius, step = protocol["point_tolerance_px"], protocol["sample_step_frames"]
    start_tolerance, end_tolerance = protocol["event_start_tolerance_s"], protocol["event_end_tolerance_s"]
    if (type(count) is not int or count <= 0 or not finite(fps) or fps <= 0
            or any(not finite(value) or value <= 0 for value in (width, height, radius, start_tolerance, end_tolerance))
            or type(step) is not int or step <= 0):
        raise ValueError("Invalid protocol limits")
    windows = protocol["closed_event_windows_s"]
    previous = 0
    for start, end in windows:
        if not all(finite(value) for value in (start, end)) or not previous <= start < end <= count / fps:
            raise ValueError("Event windows must be ordered, disjoint and inside video")
        previous = end
    expected = set()
    previous = 0
    for start, end in protocol["point_windows_frames"]:
        if type(start) is not int or type(end) is not int or not previous <= start < end <= count:
            raise ValueError("Point windows must be ordered, disjoint and inside video")
        expected.update(range(start, end, step))
        previous = end
    labels = {}
    for point in review["points"]:
        frame, visibility, center = point["frame"], point["visibility"], point["center_px"]
        if type(frame) is not int or frame in labels or frame not in expected or visibility not in ("visible", "uncertain", "absent"):
            raise ValueError("Invalid/duplicate point label")
        if visibility == "visible":
            if (not isinstance(center, list) or len(center) != 2 or not all(finite(value) for value in center)
                    or not 0 <= center[0] < width or not 0 <= center[1] < height):
                raise ValueError("Visible point must have a finite in-image centre")
        elif center is not None:
            raise ValueError("Uncertain/absent point must not invent a location")
        labels[frame] = point
    if set(labels) != expected or not expected:
        raise ValueError("All scheduled sample frames require an explicit label")
    rows, errors = [], []
    tp = fp = fn = skipped = missed_run = max_missed_run = 0
    previous_label = None
    frames_read = 0
    with (folder / "ball.jsonl").open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            if (row["frame"] != index or not finite(row["time_s"]) or abs(row["time_s"] - index / fps) > 1e-5):
                raise ValueError("Sequence missing/repeated frames or wrong clock")
            frames_read += 1
            if index not in labels:
                continue
            label, ball = labels[index], row["ball"]
            if ball is not None:
                center = ball["center_px"]
                if (len(center) != 2 or not all(finite(value) for value in center)
                        or not 0 <= center[0] < width or not 0 <= center[1] < height):
                    raise ValueError("Invalid predicted point")
            if label["visibility"] == "uncertain":
                skipped += 1
                missed_run = 0
                rows.append({"frame": index, "status": "uncertain_not_scored"})
                previous_label = index
                continue
            error = math.dist(ball["center_px"], label["center_px"]) if ball is not None and label["visibility"] == "visible" else None
            if error is not None:
                errors.append(error)
            matched = error is not None and error <= radius
            if label["visibility"] == "visible":
                tp += matched
                fn += not matched
                fp += ball is not None and not matched
            else:
                fp += ball is not None
            if previous_label is None or index - previous_label != step:
                missed_run = 0
            missed_run = missed_run + 1 if label["visibility"] == "visible" and not matched else 0
            max_missed_run = max(max_missed_run, missed_run)
            rows.append({"frame": index, "status": "correct_absence" if label["visibility"] == "absent" and ball is None else "matched" if matched else "missed" if ball is None else "wrong_point" if error is not None else "unexpected_prediction",
                         "error_px": error, "reference_px": label["center_px"],
                         "predicted_px": ball["center_px"] if ball else None})
            previous_label = index
    if frames_read != count:
        raise ValueError("Sequence frame count differs")

    supported = report.get("event_classes", ["pass"])
    if any(kind not in ("pass", "shot") for kind in supported):
        raise ValueError("Unsupported event class")
    references = review["events"]
    ids = set()
    for event in references:
        if (event["id"] in ids or event["kind"] not in ("pass", "shot") or event.get("status") != "reviewed_likely" or event.get("group") not in ("A", "B")
                or not all(finite(event[key]) for key in ("start_s", "end_s"))
                or not event["start_s"] < event["end_s"] or not in_windows(event["start_s"], event["end_s"], windows)):
            raise ValueError("Invalid reference event")
        ids.add(event["id"])
    event_results = {}
    for kind, key in (("pass", "possible_passes"), ("shot", "possible_shots")):
        reference = [event for event in references if event["kind"] == kind]
        predicted, unscored = [], 0
        for event in report.get(key, []):
            if (event.get("kind") != f"possible_{kind}" or event.get("status") != "unverified" or event.get("group") not in ("A", "B")
                    or not all(finite(event[k]) for k in ("start_s", "end_s"))
                    or not 0 <= event["start_s"] < event["end_s"] <= count / fps):
                raise ValueError("Invalid predicted event")
            if in_windows(event["start_s"], event["end_s"], windows):
                predicted.append(event)
            else:
                unscored += 1
        if kind not in supported:
            if predicted or unscored:
                raise ValueError("Predictions contradict unsupported class")
            event_results[kind] = {"status": "not_implemented", "reference_count": len(reference),
                                   **{field: None for field in ("tp", "fp", "fn", "precision", "recall", "f1")}}
            continue
        matches = match_events(predicted, reference, start_tolerance, end_tolerance)
        found = {match["reference_id"] for match in matches}
        event_results[kind] = {"status": "development_timing_diagnostic", "reference_count": len(reference),
                              "predictions_in_scope": len(predicted), "predictions_outside_scope": unscored,
                              **scores(len(matches), len(predicted) - len(matches), len(reference) - len(matches)),
                              "matches": matches, "missed_reference_ids": [event["id"] for event in reference if event["id"] not in found]}
    ordered = sorted(errors)
    return {"kind": "ball_sequence_development_audit_v1", "source_sha256": protocol["source_sha256"],
            "person_job_id": protocol["person_job_id"], "independently_validated": False,
            "point_diagnostic": {**scores(tp, fp, fn), "scheduled_samples": len(expected), "uncertain_skipped": skipped,
                                 "visible_samples": sum(point["visibility"] == "visible" for point in labels.values()),
                                 "tolerance_px": radius, "max_consecutive_missed_samples": max_missed_run,
                                 "median_error_px_when_predicted": (ordered[len(ordered)//2] if len(ordered) % 2 else sum(ordered[len(ordered)//2-1:len(ordered)//2+1])/2) if ordered else None,
                                 "max_error_px_when_predicted": max(errors) if errors else None, "rows": rows},
            "event_diagnostic": event_results, "closed_event_windows_s": windows,
            "reviewed_events": [{key: event[key] for key in ("id", "kind", "group", "start_s", "end_s")} for event in references],
            "warning": "Tiny same-agent development review, not independent accuracy/AP/event acceptance. Event matching checks class, colour and timing only, not player identity. No positive shots cannot establish shot recall. Production confirmed totals stay null."}


def run(folder, protocol_path, review_path, output):
    paths = [path.resolve() for path in (folder, protocol_path, review_path, output)]
    if any(not path.is_relative_to(ROOT) for path in paths) or output.exists():
        raise ValueError("Use workspace paths and a new output")
    result = evaluate(folder, json.loads(protocol_path.read_text(encoding="utf-8")), json.loads(review_path.read_text(encoding="utf-8")))
    result["input_sha256"] = {}
    for label, path in (("protocol", protocol_path), ("review", review_path), ("predictions", folder / "report.json"), ("sequence", folder / "ball.jsonl")):
        with path.open("rb") as stream:
            result["input_sha256"][label] = hashlib.file_digest(stream, "sha256").hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = run(args.folder, args.protocol, args.review, args.output)
    print(json.dumps({"point_diagnostic": {key: value for key, value in report["point_diagnostic"].items() if key != "rows"},
                      "event_diagnostic": report["event_diagnostic"]}, ensure_ascii=False))
