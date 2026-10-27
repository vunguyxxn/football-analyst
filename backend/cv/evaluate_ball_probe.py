"""Sparse point-localization diagnostic; never infer event quality from it."""
import argparse
import json
import math
from pathlib import Path


def evaluate(predictions, review):
    if predictions["source_sha256"] != review["source_sha256"]:
        raise ValueError("Review source differs from predictions")
    by_frame = {sample["frame"]: sample for sample in predictions["samples"]}
    threshold, radius = review["score_threshold"], review["center_tolerance_px"]
    if not 0 <= threshold <= 1 or not math.isfinite(radius) or radius <= 0:
        raise ValueError("Invalid review thresholds")
    true_positive = false_positive = false_negative = skipped = 0
    rows = []
    for frame in review["frames"]:
        if frame["visibility"] != "visible":
            skipped += 1
            continue
        if frame["frame"] not in by_frame:
            raise ValueError("Predictions missing a reviewed frame")
        x, y = frame["center"]
        candidates = [candidate for candidate in by_frame[frame["frame"]]["candidates"] if candidate["score"] >= threshold]
        distances = [math.hypot((box["xyxy"][0] + box["xyxy"][2]) / 2 - x,
                                (box["xyxy"][1] + box["xyxy"][3]) / 2 - y) for box in candidates]
        matched = bool(distances) and min(distances) <= radius
        true_positive += matched
        false_positive += len(candidates) - int(matched)
        false_negative += not matched
        rows.append({"frame": frame["frame"], "matched": matched, "candidate_count": len(candidates),
                     "closest_error_px": min(distances) if distances else None})
    return {"scope": review["scope"], "score_threshold": threshold, "center_tolerance_px": radius,
            "scored_frames": len(rows), "uncertain_frames_skipped": skipped,
            "point_matches": true_positive, "unmatched_candidates": false_positive, "missed_visible_points": false_negative,
            "precision_proxy": true_positive / (true_positive + false_positive) if true_positive + false_positive else None,
            "recall_proxy": true_positive / (true_positive + false_negative) if true_positive + false_negative else None,
            "rows": rows, "warning": "Tiny agent-labelled development sample; not independent accuracy, bounding-box AP, tracking quality or event F1."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("review", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.predictions.read_text(encoding="utf-8")),
                              json.loads(args.review.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
