"""Pinned, sparse video diagnostic for original and fine-tuned person weights."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
from unittest.mock import patch

from backend.cv.evaluate_video_review import canonical_hash, error_stats, evaluate_frame, point_labels, summarize
from backend.cv.prepare_video_review import digest, workspace_path


def recording_tracker(base, stream, sampled, counts):
    """Observe tracker output without changing its inputs, results or state."""
    class RecordingTracker(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.record_frame = 0

        def update_with_detections(self, detections):
            result = super().update_with_detections(detections)
            rows = [{"track_id": int(identity), "team": "unknown", "box": box.tolist(),
                     "image_xy": [float((box[0] + box[2]) / 2), float(box[3])]}
                    for box, identity in zip(result.xyxy, result.tracker_id)]
            stream.write(json.dumps({"frame": self.record_frame, "people": rows}) + "\n")
            counts["frames"] += 1
            counts["observations"] += len(rows)
            counts["nonempty_frames"] += bool(rows)
            if self.record_frame in sampled:
                sampled[self.record_frame] = rows
            if self.record_frame % 300 == 0:
                print(f"frame {self.record_frame}", flush=True)
            self.record_frame += 1
            return result
    return RecordingTracker


def evaluate_samples(labels, samples, protocol):
    trials = []
    for gate in protocol["sensitivity_gates_px"]:
        frames = [{"frame": frame, "clip": "return",
                   **evaluate_frame(point_labels(labels["frames"][str(frame)]), samples[frame], gate)}
                  for frame in protocol["frames"]]
        trials.append({"gate_px": gate, "frames": frames,
                       "summary": summarize(frames, protocol["max_sample_gap_frames"])})
    return trials


def paired_diagnostics(runs, protocol):
    """Compare identical label/frame pairs and eligible identity intervals."""
    result = []
    for gate in protocol["sensitivity_gates_px"]:
        indexed = {}
        for name, run_result in runs.items():
            trial = next(t for t in run_result["evaluation"] if t["gate_px"] == gate)
            indexed[name] = {f["frame"]: {m["identity"]: m for m in f["matches"] if not m["ambiguous"]}
                             for f in trial["frames"]}
        errors = {name: [] for name in runs}
        changes = {name: [] for name in runs}
        intervals = 0
        for frame in protocol["frames"]:
            common = set.intersection(*(set(rows[frame]) for rows in indexed.values()))
            for identity in sorted(common):
                for name, rows in indexed.items():
                    errors[name].append(rows[frame][identity]["distance_px"])
        for previous, current in zip(protocol["frames"], protocol["frames"][1:]):
            if current - previous > protocol["max_sample_gap_frames"]:
                continue
            common = set.intersection(*(set(rows[previous]) & set(rows[current]) for rows in indexed.values()))
            intervals += len(common)
            for identity in sorted(common):
                for name, rows in indexed.items():
                    before, after = rows[previous][identity]["track_id"], rows[current][identity]["track_id"]
                    if before != after:
                        changes[name].append({"identity": identity, "previous_frame": previous,
                                              "frame": current, "from_track": before, "to_track": after})
        result.append({"gate_px": gate, "common_unambiguous_pixel_errors": {k: error_stats(v) for k, v in errors.items()},
                       "common_sampled_identity_intervals": intervals, "apparent_identity_changes": changes})
    return result


def run(protocol_path, output):
    output = workspace_path(output)
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads(workspace_path(protocol_path).read_text(encoding="utf-8"))
    for name, expected in protocol["input_sha256"].items():
        if digest(workspace_path(name)) != expected:
            raise ValueError(f"Input hash mismatch: {name}")
    labels = json.loads(workspace_path(protocol["labels"]).read_text(encoding="utf-8"))
    if labels["source_sha256"] != digest(workspace_path(protocol["source"])):
        raise ValueError("Labels and video differ")
    root = Path(__file__).resolve().parents[2]
    os.environ["YOLO_CONFIG_DIR"] = str(root / "data/processed")
    os.environ["MPLCONFIGDIR"] = str(root / ".tmp/matplotlib")
    os.environ["YOLO_AUTOINSTALL"] = "false"
    import cv2
    import supervision as sv
    import torch
    from backend.cv.track_video import track_video
    cv2.setNumThreads(4)
    torch.set_num_threads(4)
    torch.manual_seed(20261023)
    output.mkdir(parents=True)
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    runs = {}
    for name, weights in protocol["models"].items():
        print(name, flush=True)
        folder = output / name
        folder.mkdir()
        sampled = dict.fromkeys(protocol["frames"])
        counts = Counter()
        with (folder / "tracker.jsonl").open("w", encoding="utf-8") as stream:
            tracker = recording_tracker(sv.ByteTrack, stream, sampled, counts)
            with patch.object(sv, "ByteTrack", tracker):
                summary = track_video(
                    workspace_path(protocol["source"]), folder / "tracked.mp4", workspace_path(weights),
                    device="0", image_size=protocol["image_size"], confidence=protocol["confidence"],
                    chunk_seconds=10, team_samples=workspace_path(protocol["team_samples"]),
                    calibration=workspace_path(protocol["calibration"]), pitch_output=folder / "pitch",
                    compensate_camera=True, landmark_checks=workspace_path(protocol["landmark_checks"]),
                    on_pitch_only=True, smooth_pitch=False)
        if any(value is None for value in sampled.values()):
            raise ValueError("Video ended before all evaluation frames")
        if summary["frames"] != protocol["video_frames"] or counts["frames"] != protocol["video_frames"]:
            raise ValueError("Unexpected video/recorder frame count")
        with (folder / "pitch/tracking.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row["frame"] in sampled:
                    for prediction in sampled[row["frame"]]:
                        if prediction["track_id"] == row["track_id"]:
                            prediction["team"] = row["team"]
        camera = {}
        with (folder / "pitch/camera_quality.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                camera[row["frame"]] = row["status"]
        runs[name] = {"run": summary, "tracker_counts": dict(counts),
                      "camera_status_counts": dict(Counter(camera.values())),
                      "sample_camera_status": {f: camera[f] for f in sampled},
                      "samples": sampled, "evaluation": evaluate_samples(labels, sampled, protocol)}
        (folder / "result.json").write_text(json.dumps(runs[name], indent=2), encoding="utf-8")
        print(json.dumps({"name": name, "counts": dict(counts)}), flush=True)
    for name, expected in protocol["input_sha256"].items():
        if digest(workspace_path(name)) != expected:
            raise ValueError(f"Input changed during run: {name}")
    report = {"kind": "yolo_person_video_comparison_v1", "protocol": protocol,
              "protocol_canonical_sha256": canonical_hash(protocol), "runs": runs,
              "paired_diagnostics": paired_diagnostics(runs, protocol),
              "independent_ground_truth": False, "pipeline_promoted": False,
              "warning": "Sparse agent-label diagnostic; not detection recall, MOTA, IDF1 or independent match evaluation"}
    (output / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    make_montage(output, protocol)
    return report


def make_montage(output, protocol):
    import cv2
    import numpy as np
    rows = []
    for frame_number in (protocol["frames"][0], protocol["frames"][2], protocol["frames"][-1]):
        panels = []
        for name in protocol["models"]:
            cap = cv2.VideoCapture(str(output / name / "tracked.mp4"))
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Cannot read comparison video")
            finally:
                cap.release()
            panel = cv2.resize(frame, (640, 360))
            cv2.rectangle(panel, (0, 0), (640, 28), (0, 0, 0), -1)
            cv2.putText(panel, f"{name} / frame {frame_number}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            panels.append(panel)
        rows.append(np.hstack(panels))
    if not cv2.imwrite(str(output / "comparison.jpg"), np.vstack(rows)):
        raise ValueError("Cannot write comparison montage")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run("docs/fixtures/yolo_person_video_protocol_v1.json", args.output)
