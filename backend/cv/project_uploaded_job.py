"""Provisional metric estimates from source-locked manual calibration, not survey truth."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from backend.common.schemas import TrackingRow
from backend.cv.camera_motion import CameraMotion
from backend.cv.circle_calibration import fit_circle_pixels, circle_matrix
from backend.cv.pitch_metrics import PitchMetrics
from backend.cv.pitch_smoother import PitchSmoother
from backend.cv.homography import matrix_for, refined_matrix_for

ROOT = Path(__file__).resolve().parents[2]


def project_job(job, controls_path, output):
    job, controls_path, output = (path.resolve() for path in (job, controls_path, output))
    if any(not path.is_relative_to(ROOT) for path in (job, controls_path, output)) or output.exists():
        raise ValueError("Use workspace paths and a new output")
    status = json.loads((job / "status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Job must be completed")
    result = status["result"]
    source = next(job.glob("source.*"))
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    if controls["source_sha256"] != digest or controls["image_size"] != [result["width"], result["height"]] or controls.get("pitch_m") != [105, 68]:
        raise ValueError("Calibration source/dimensions differ")
    previous_end = 0
    for anchor in controls["anchors"]:
        end = anchor.get("end_frame", min(result["frames"], anchor["frame"] + 300))
        if not previous_end <= anchor["frame"] < end <= result["frames"]:
            raise ValueError("Calibration windows overlap or exceed clip")
        previous_end = end
    anchors = {anchor["frame"]: anchor for anchor in controls["anchors"]}
    output.mkdir(parents=True)
    motion, metrics, smoother = CameraMotion(), PitchMetrics(result["fps"]), PitchSmoother()
    capture = cv2.VideoCapture(str(source))
    segment = -1
    qualities, role_counts, source_frames = Counter(), defaultdict(Counter), set()
    intervals, current_interval = [], None
    index = accepted = outside = 0
    anchor_quality = []
    active_end = None
    small_size = (result["width"] // 2, result["height"] // 2)
    sx, sy = result["width"] / small_size[0], result["height"] / small_size[1]
    down, up = np.diag([sx, sy, 1.]), np.diag([1 / sx, 1 / sy, 1.])
    try:
        with (output / "tracking.jsonl").open("w", encoding="utf-8") as tracking:
            for chunk_index in range(result["chunks"]):
                chunk = json.loads((job / f"chunk-{chunk_index}.json").read_text(encoding="utf-8"))
                for record in chunk["frames"]:
                    ok, frame = capture.read()
                    if not ok or record["frame"] != index:
                        raise ValueError("Video and detections differ")
                    anchor_matrix = None
                    if index in anchors:
                        anchor = anchors[index]
                        if "image_points" in anchor:
                            fit = {"method": "manual_points"}
                            matrix = matrix_for(anchor["image_points"], anchor["pitch_points"])
                            if anchor.get("extra_image_points"):
                                matrix = refined_matrix_for(anchor["image_points"], anchor["pitch_points"], anchor["extra_image_points"], anchor["extra_pitch_points"])
                            quality = {}
                            if anchor.get("check_image_points"):
                                projected = cv2.perspectiveTransform(np.float64([anchor["check_pitch_points"]]), np.linalg.inv(matrix))[0]
                                errors = np.linalg.norm(projected - anchor["check_image_points"], axis=1)
                                quality["heldout_pixel_errors"] = errors.tolist()
                                if max(errors) > anchor["max_check_error_px"]:
                                    raise ValueError("Held-out landmark checks failed")
                        else:
                            ellipse, fit = fit_circle_pixels(frame, (tuple(anchor["ellipse_center"]), tuple(anchor["ellipse_size"]), 0))
                            matrix, quality = circle_matrix(ellipse, anchor["near"], anchor["far"])
                        anchor_quality.append({"frame": index, **fit, **quality})
                        anchor_matrix = matrix @ down
                        segment += 1
                        active_end = anchor.get("end_frame", index + 300)
                    small = cv2.resize(frame, small_size)
                    boxes = np.array([box["xyxy"] for box in record["boxes"]], dtype=float).reshape(-1, 4)
                    if active_end is None or index >= active_end:
                        motion.matrix = motion.previous = motion.mask = None
                        quality = {"status": "uncalibrated"}
                    else:
                        quality = motion.update(small, boxes / [sx, sy, sx, sy], anchor=anchor_matrix)
                    qualities[quality["status"]] += 1
                    if motion.matrix is not None:
                        if current_interval is None:
                            current_interval = {"start_s": index / result["fps"], "end_s": (index + 1) / result["fps"]}
                        else:
                            current_interval["end_s"] = (index + 1) / result["fps"]
                        inverse = motion.matrix @ up
                        smoother.advance(index / result["fps"])
                        for box in record["boxes"]:
                            left, top, right, bottom = box["xyxy"]
                            xy = inverse @ [(left + right) / 2, bottom, 1.]
                            if abs(xy[2]) < 1e-9:
                                continue
                            x, y = xy[:2] / xy[2]
                            if not np.isfinite([x, y]).all() or not 0 <= x <= 105 or not 0 <= y <= 68:
                                outside += 1
                                continue
                            row = TrackingRow(frame=index, time_s=index / result["fps"], track_id=box["id"], team=box["group"], x_m=float(x), y_m=float(y))
                            row, broken, _ = smoother.observe(segment, row)
                            if broken:
                                metrics.break_chain(segment, box["id"])
                            if row is None:
                                continue
                            tracking.write(row.model_dump_json() + "\n")
                            metrics.observe(segment, row)
                            role_counts[(segment, row.track_id)][row.team] += 1
                            accepted += 1
                            source_frames.add(index)
                    elif current_interval is not None:
                        intervals.append(current_interval)
                        current_interval = None
                    index += 1
                print(json.dumps({"frames": index, "accepted_positions": accepted, "camera_status": dict(qualities)}), flush=True)
    finally:
        capture.release()
    if current_interval:
        intervals.append(current_interval)
    if index != result["frames"]:
        raise ValueError("Frame count mismatch")
    raw = metrics.report()
    groups = {group: np.zeros((14, 21), dtype=float) for group in ("A", "B", "unknown")}
    players = []
    for track in raw["tracks"]:
        roles = role_counts[(track["segment"], track["track_id"])]
        group, support = roles.most_common(1)[0]
        if support / sum(roles.values()) < .7:
            group = "unknown"
        groups[group] += np.array(track["heatmap"]) / result["fps"]
        players.append({"segment": track["segment"], "id": track["track_id"], "group": group,
                        "distance_m": track["distance_m"], "motion_s": track["duration_s"],
                        "mean_speed_kmh": track["distance_m"] / track["duration_s"] * 3.6 if track["duration_s"] else None,
                        "maximum_speed_kmh": track["max_speed_kmh"] if track["duration_s"] else None,
                        "heatmap_seconds": (np.array(track["heatmap"]) / result["fps"]).tolist(),
                        "rejected_intervals": track["rejected_steps"]})
    players.sort(key=lambda player: -player["motion_s"])
    report = {"kind": "uploaded_pitch_estimate_v1", "source_sha256": digest, "person_job_id": job.name,
              "quality": "provisional_manual_calibration_not_independently_validated",
              "pitch_m": [105, 68], "origin": "bottom_left", "duration_s": result["frames"] / result["fps"],
              "calibrated_intervals": intervals, "camera_status": dict(qualities), "frames_with_positions": len(source_frames),
              "accepted_positions": accepted, "outside_rejected": outside, "anchor_quality": anchor_quality,
              "groups": [{"group": group, "heatmap_seconds": heatmap.tolist()} for group, heatmap in groups.items()],
              "players": players, "limits": ["Ước lượng từ mốc sân do agent chọn, chưa kiểm chứng sai số bằng mốc độc lập.",
              "Sân giả định 105×68 m; chỉ tính đoạn camera còn theo dõi được. Không nối ID qua mốc hiệu chỉnh hoặc khoảng mất dấu.",
              "Nhóm áo/ID chưa xác nhận danh tính; quãng đường chỉ là phần quan sát hợp lệ, không phải tổng vận động toàn trận."]}
    report["segments"] = [{"segment": i, "start_s": anchor["frame"] / result["fps"], "end_s": min(result["frames"], anchor.get("end_frame", anchor["frame"] + 300)) / result["fps"]} for i, anchor in enumerate(controls["anchors"])]
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("controls", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = project_job(args.job, args.controls, args.output)
    print(json.dumps({key: value for key, value in report.items() if key not in ("groups", "players")}))
