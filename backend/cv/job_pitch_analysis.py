"""Upload pipeline: bounded camera propagation, guarded provisional coordinates.

Internal job artifacts only; shared TrackingRow and 105x68 contract unchanged.
"""
from collections import Counter, defaultdict
import hashlib
import json
import threading
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from backend.common.schemas import TrackingRow
from backend.cv.camera_motion import CameraMotion
from backend.cv.homography import matrix_for
from backend.cv.pitch_circle_keypoints import white_pitch_pixels
from backend.cv.pitch_keypoints import project
from backend.cv.pitch_line_calibration import fit_line_pitch
from backend.cv.pitch_metrics import PitchMetrics
from backend.cv.pitch_smoother import PitchSmoother
from backend.cv.upload_analysis import AnalysisCancelled

WEIGHTS = Path(__file__).resolve().parents[2] / "data/raw/pitch_keypoints/roboflow-football-pitch.pt"
WEIGHTS_HASH = "28f68f7c4056d6d9b137efd2e7ab5f3c494039380c63831649126ced25628b36"
MAX_POSITIONS = 180000
MAX_POSITION_BYTES = 18*1024*1024
_artifact_lock = threading.RLock()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    with _artifact_lock:
        path = Path(path)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(path)


def read_json(path):
    with _artifact_lock:
        return json.loads(Path(path).read_text(encoding="utf-8"))


def pitch_folder(folder):
    pointer = folder / "pitch-current.json"
    if not pointer.is_file():
        return folder / "pitch_estimate"
    version = read_json(pointer)["version"]
    if len(version) != 32 or any(char not in "0123456789abcdef" for char in version):
        raise ValueError("Invalid pitch version")
    return folder / "pitch_runs" / version


def validate_manual(payload, info):
    """Four fitting landmarks and two distinct, held-out metre checks."""
    if payload["source_sha256"] != info["source_sha256"]:
        raise ValueError("Mốc sân không khớp video hiện tại.")
    frame = payload["frame"]
    if type(frame) is not int or not 0 <= frame < info["frames"]:
        raise ValueError("Thời điểm hiệu chỉnh nằm ngoài video.")
    image, pitch = np.asarray(payload["image_points"], float), np.asarray(payload["pitch_points"], float)
    if (image.shape != (6, 2) or pitch.shape != (6, 2) or not np.isfinite(image).all()
            or not np.isfinite(pitch).all() or np.any(image < 0)
            or np.any(image >= [info["width"], info["height"]]) or np.any(pitch < 0)
            or np.any(pitch > [105, 68]) or len(np.unique(image, axis=0)) != 6
            or len(np.unique(pitch, axis=0)) != 6):
        raise ValueError("Cần 6 mốc khác nhau trong ảnh và sân: 4 mốc hiệu chỉnh, 2 mốc đối chiếu.")
    matrix = matrix_for(image[:4], pitch[:4])
    forward = np.linalg.inv(matrix)
    denominators = np.c_[[0, 105, 105, 0], [0, 0, 68, 68], np.ones(4)] @ forward[2]
    if not (np.all(denominators > 0) or np.all(denominators < 0)):
        raise ValueError("Các mốc tạo phép chiếu không hợp lệ. Hãy chọn lại đúng giao vạch.")
    errors = np.linalg.norm(project(matrix, image[4:]) - pitch[4:], axis=1)
    if np.max(errors) > 1:
        raise ValueError(f"Hai mốc đối chiếu lệch tối đa {max(errors):.2f}m (giới hạn 1m). Hãy kiểm tra lại mốc.")
    return matrix


def validate_manual_frame(source, payload, info):
    matrix = validate_manual(payload, info)
    capture = cv2.VideoCapture(str(source))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, payload["frame"])
        ok, frame = capture.read()
        if not ok:
            raise ValueError("Không đọc được khung hình đã chọn.")
        if not projection_quality(frame, matrix)["passed"]:
            raise ValueError("Mốc chưa bám đúng các vạch sân. Hãy phóng to ảnh để chọn chính xác hoặc chụp khung rõ hơn. Kết quả hiện tại được giữ nguyên.")
    finally:
        capture.release()
    return matrix


def projection_quality(frame, matrix):
    """Visible painted markings validate propagation, never refit the matrix."""
    height, width = frame.shape[:2]
    pixels = white_pitch_pixels(frame)
    if not len(pixels):
        return {"passed": False, "markings": [], "reason": "no_white_markings", "independently_validated": False}
    mask = np.ones((height, width), np.uint8)
    if len(pixels):
        xx, yy = pixels.astype(int).T
        mask[yy, xx] = 0
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    forward = np.linalg.inv(matrix)
    markings = [("halfway", [52.5, 0], [52.5, 68], "x"),
                ("far", [0, 68], [105, 68], "y"), ("near", [0, 0], [105, 0], "y")]
    for x, goal in ((16.5, 0), (88.5, 105)):
        markings.extend([(f"front{x}", [x, 13.84], [x, 54.16], "x"),
                         (f"side{x}a", [x, 13.84], [goal, 13.84], "y"),
                         (f"side{x}b", [x, 54.16], [goal, 54.16], "y")])
    results = []
    for name, a, b, family in markings:
        xy = project(forward, np.linspace(a, b, 160))
        xy = xy[(xy[:, 0] >= 4) & (xy[:, 0] < width-4) & (xy[:, 1] >= 4) & (xy[:, 1] < height-4)]
        if len(xy) < 20 or np.linalg.norm(xy[-1]-xy[0]) < 120:
            continue
        xx, yy = np.rint(xy).astype(int).T
        residual = distance[yy, xx]
        passed = bool(np.median(residual) <= 4 and np.mean(residual <= 5) >= .65)
        results.append({"marking": name, "family": family, "passed": passed})
    theta = np.linspace(0, 2*np.pi, 240)
    xy = project(forward, np.c_[52.5+9.15*np.cos(theta), 34+9.15*np.sin(theta)])
    xy = xy[(xy[:, 0] >= 4) & (xy[:, 0] < width-4) & (xy[:, 1] >= 4) & (xy[:, 1] < height-4)]
    if len(xy) >= 40:
        xx, yy = np.rint(xy).astype(int).T
        residual = distance[yy, xx]
        results.append({"marking": "circle", "family": "curve", "passed": bool(np.median(residual) <= 4 and np.mean(residual <= 5) >= .65)})
    families = {item["family"] for item in results if item["passed"]}
    passed = len(results) >= 3 and all(item["passed"] for item in results) and {"x", "y"} <= families
    return {"passed": passed, "markings": results, "independently_validated": False}


def automatic_finder():
    if not WEIGHTS.is_file() or digest(WEIGHTS) != WEIGHTS_HASH:
        return None
    import torch
    from ultralytics import YOLO
    model = YOLO(str(WEIGHTS))
    if model.task != "pose" or model.model.yaml.get("kpt_shape") != [32, 3]:
        return None
    device = 0 if torch.cuda.is_available() else "cpu"

    def find(frame):
        result = model.predict(frame, imgsz=640, device=device, conf=.25, verbose=False)[0]
        if len(result.boxes) != 1 or result.keypoints is None:
            return None
        fit = fit_line_pitch(frame, result.keypoints.xy[0].cpu().numpy(), result.keypoints.conf[0].cpu().numpy())
        return np.asarray(fit["matrix"]) if fit["status"] == "candidate" else None
    return find


def analyze_pitch(source, folder, info, progress, cancelled, *, finder_factory=automatic_finder,
                  quality=projection_quality, motion_factory=CameraMotion, force_automatic=False):
    """Write an immutable version; pointer changes only after all artifacts exist."""
    if not {"width", "height", "fps", "frames", "chunks"} <= info.keys():
        return {"status": "needs_input", "message": "Tracking thiếu thông số để hiệu chỉnh sân."}
    if digest(source) != info["source_sha256"]:
        raise ValueError("Video không khớp dữ liệu tracking.")
    controls_path = folder / "manual-pitch.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8")) if controls_path.is_file() else []
    anchors = {item["frame"]: validate_manual(item, info) for item in controls}
    # Manual recovery must work even if CUDA/weights are unavailable.
    finder = finder_factory() if force_automatic or not controls else None
    saved_auto_path = folder / "automatic-pitch.json"
    saved_auto = read_json(saved_auto_path) if saved_auto_path.is_file() else {}
    scheduled_auto = {item["frame"]: np.asarray(item["matrix"], float) for item in saved_auto.get("anchors", [])} if saved_auto.get("source_sha256") == info["source_sha256"] else {}
    version = uuid4().hex
    output = folder / "pitch_runs" / version
    output.mkdir(parents=True)
    capture = cv2.VideoCapture(str(source))
    motion, smoother, metrics = motion_factory(), PitchSmoother(), PitchMetrics(info["fps"])
    small_size = (max(1, info["width"]//2), max(1, info["height"]//2))
    sx, sy = info["width"]/small_size[0], info["height"]/small_size[1]
    down, up = np.diag([sx, sy, 1.]), np.diag([1/sx, 1/sy, 1.])
    interval = max(1, round(info["fps"]))
    pending, segments, anchor_log = [], [], []
    rejected_manual_frames = []
    statuses, roles, frames_seen = Counter(), defaultdict(Counter), set()
    index = accepted = outside = written_bytes = 0
    segment = -1
    limit_reached = False

    def flush(stream):
        nonlocal accepted, written_bytes, limit_reached
        for frame_id, rows in pending:
            if not segments or segments[-1]["segment"] != segment:
                segments.append({"segment": segment, "start_s": frame_id/info["fps"], "end_s": (frame_id+1)/info["fps"]})
            else:
                segments[-1]["end_s"] = (frame_id+1)/info["fps"]
            smoother.advance(frame_id/info["fps"])
            for raw in rows:
                row, broken, _ = smoother.observe(segment, raw)
                if broken:
                    metrics.break_chain(segment, raw.track_id)
                if row is None:
                    continue
                encoded = row.model_dump_json()+"\n"
                if accepted >= MAX_POSITIONS or written_bytes+len(encoded.encode()) > MAX_POSITION_BYTES:
                    limit_reached = True
                    return
                stream.write(encoded)
                written_bytes += len(encoded.encode())
                accepted += 1
                frames_seen.add(frame_id)
                roles[(segment, row.track_id)][row.team] += 1
                metrics.observe(segment, row)

    try:
        with (output / "tracking.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            for chunk_index in range(info["chunks"]):
                chunk = json.loads((folder / f"chunk-{chunk_index}.json").read_text(encoding="utf-8"))
                for record in chunk["frames"]:
                    if cancelled():
                        raise AnalysisCancelled()
                    ok, frame = capture.read()
                    if not ok or record["frame"] != index:
                        raise ValueError("Video và tracking không đồng bộ.")
                    anchor, method = anchors.get(index), "manual"
                    if anchor is None and index in scheduled_auto:
                        anchor, method = scheduled_auto[index], "automatic"
                    if anchor is None and finder and index % interval == 0 and (motion.matrix is None or motion.age >= 270):
                        anchor, method = finder(frame), "automatic"
                    if anchor is not None:
                        initial_check = quality(frame, anchor)
                        if not initial_check["passed"] and method == "manual":
                            rejected_manual_frames.append(index)
                            fallback = scheduled_auto.get(index)
                            if fallback is not None and quality(frame, fallback)["passed"]:
                                anchor, method = fallback, "automatic"
                                initial_check = {"passed": True}
                        if initial_check["passed"]:
                            # Never bridge metrics or unclosed pending frames across anchors.
                            pending.clear()
                            segment += 1
                            anchor_log.append({"frame": index, "method": method, "matrix": anchor.tolist()})
                        else:
                            anchor = None
                    boxes = np.asarray([box["xyxy"] for box in record["boxes"]], float).reshape(-1, 4)
                    state = motion.update(cv2.resize(frame, small_size), boxes/[sx, sy, sx, sy], anchor=anchor @ down if anchor is not None else None)
                    if motion.matrix is None:
                        pending.clear()
                        statuses[state.get("reason", "uncalibrated")] += 1
                    else:
                        matrix = motion.matrix @ up
                        check_due = anchor is not None or index % interval == 0 or index == info["frames"]-1
                        valid = not check_due or quality(frame, matrix)["passed"]
                        if not valid:
                            pending.clear()
                            motion = motion_factory()
                            statuses["marking_check_failed"] += 1
                        else:
                            rows = []
                            for box in record["boxes"]:
                                left, _, right, bottom = box["xyxy"]
                                try:
                                    x, y = project(matrix, [[(left+right)/2, bottom]])[0]
                                except ValueError:
                                    continue
                                if not 0 <= x <= 105 or not 0 <= y <= 68:
                                    outside += 1
                                    continue
                                rows.append(TrackingRow(frame=index, time_s=index/info["fps"], track_id=box["id"], team=box["group"], x_m=float(x), y_m=float(y)))
                            pending.append((index, rows))
                            if check_due:
                                flush(stream)
                                pending.clear()
                            statuses["geometrically_supported"] += 1
                    index += 1
                    if index % interval == 0:
                        progress(progress=70+29*index/info["frames"], stage="Đang hiệu chỉnh sân và tổng hợp heatmap", processed_frames=index, total_frames=info["frames"])
                    if limit_reached:
                        break
                if limit_reached:
                    break
        if index != info["frames"] and not limit_reached:
            raise ValueError("Thiếu khung hình khi hiệu chỉnh.")
        if cancelled():
            raise AnalysisCancelled()
        if not accepted:
            return {"status": "needs_input", "message": "Mốc đã chọn chưa khớp vạch sân. Hãy chọn lại đúng giao điểm hoặc khung hình rõ hơn." if rejected_manual_frames else "Đã theo dõi người. Chưa có đoạn sân đủ tin cậy; hãy chọn mốc sân bên dưới.",
                    "attempted_frames": index, "camera_status": dict(statuses)}
        progress(progress=99, stage="Đang tổng hợp heatmap và phân tích chiến thuật")
        raw = metrics.report()
        groups = {group: np.zeros((14, 21)) for group in ("A", "B", "unknown", "referee")}
        players = []
        for track in raw["tracks"]:
            counts = roles[(track["segment"], track["track_id"])]
            group, support = counts.most_common(1)[0]
            if support/sum(counts.values()) < .7:
                group = "unknown"
            heatmap = np.asarray(track["heatmap"])/info["fps"]
            groups[group] += heatmap
            players.append({"segment": track["segment"], "id": track["track_id"], "group": group,
                            "distance_m": track["distance_m"], "motion_s": track["duration_s"],
                            "mean_speed_kmh": track["distance_m"]/track["duration_s"]*3.6 if track["duration_s"] else None,
                            "maximum_speed_kmh": track["max_speed_kmh"] if track["duration_s"] else None,
                            "heatmap_seconds": heatmap.tolist(), "rejected_intervals": track["rejected_steps"]})
        intervals = [{"start_s": item["start_s"], "end_s": item["end_s"]} for item in segments]
        report = {"kind": "uploaded_pitch_estimate_v1", "person_job_id": folder.name, "source_sha256": info["source_sha256"],
                  "quality": "provisional_hybrid_calibration_not_independently_validated", "pitch_m": [105, 68], "origin": "bottom_left",
                  "duration_s": info["frames"]/info["fps"], "calibrated_intervals": intervals, "segments": segments,
                  "camera_status": dict(statuses), "frames_with_positions": len(frames_seen), "accepted_positions": accepted,
                  "outside_rejected": outside, "anchor_quality": anchor_log,
                  "landmark_checks": {"enabled": bool(controls), "independently_validated": False, "results": []},
                  "groups": [{"group": g, "heatmap_seconds": h.tolist()} for g, h in groups.items()], "players": players,
                  "limits": ["Tọa độ từ mốc tự động hoặc mốc bạn chọn, được kiểm hình học; chưa kiểm chứng sai số thực địa.",
                             "Sân giả định 105×68m. Chỉ tính đoạn còn theo dõi và vượt kiểm vạch; không nối quãng đường qua mất dấu/đổi mốc.",
                             "Nhóm áo/ID chưa xác nhận danh tính, trọng tài hoặc thủ môn; không phải số liệu toàn trận."],
                  "publication": {"policy": "hybrid_opening_closing_marking_checks_v1", "tracking_sha256": digest(output / "tracking.jsonl"), "independently_validated": False}}
        from backend.tactics.video_tactics import build_report
        rows = [json.loads(line) for line in (output / "tracking.jsonl").read_text(encoding="utf-8").splitlines()]
        tactics = build_report(rows, report, info["fps"], info["frames"])
        report["tactical_windows"] = sum(w["status"] == "observed_cluster" for w in tactics["windows"])
        atomic_json(output / "report.json", report)
        atomic_json(output / "tactics.json", tactics)
        if cancelled():
            raise AnalysisCancelled()
        retained_auto = {frame: {"frame": frame, "method": "automatic", "matrix": matrix.tolist()} for frame, matrix in scheduled_auto.items()}
        retained_auto.update({item["frame"]: item for item in anchor_log if item["method"] == "automatic"})
        atomic_json(saved_auto_path, {"source_sha256": info["source_sha256"], "weights_sha256": WEIGHTS_HASH,
                                      "anchors": list(retained_auto.values())})
        atomic_json(folder / "pitch-current.json", {"version": version})
        seconds = sum(item["end_s"]-item["start_s"] for item in intervals)
        return {"status": "ready" if not limit_reached and seconds >= info["frames"]/info["fps"]*.95 else "partial",
                "message": "Một số mốc bạn chọn chưa khớp vạch sân; giữ các đoạn hợp lệ trước đó. Hãy chụp khung khác để bổ sung." if rejected_manual_frames else "Đã có phân tích cho các đoạn hiệu chỉnh hợp lệ." if not limit_reached else "Đã đạt giới hạn kết quả; hãy cắt clip ngắn hơn để phân tích phần còn lại.",
                "rejected_manual_frames": rejected_manual_frames,
                "version": version, "calibrated_seconds": seconds, "frames_with_positions": len(frames_seen),
                "duration_s": info["frames"]/info["fps"], "automatic_available": finder is not None,
                "tactical_windows": sum(w["status"] == "observed_cluster" for w in tactics["windows"])}
    finally:
        capture.release()
