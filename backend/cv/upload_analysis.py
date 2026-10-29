"""Bounded-memory image-space tracking for uploaded clips; no pitch coordinates."""
from pathlib import Path
import json
import math
import os


class AnalysisCancelled(Exception):
    pass


def video_info(source: Path) -> dict:
    import cv2
    capture = cv2.VideoCapture(str(source))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = int(capture.get(3)), int(capture.get(4))
        ok, _ = capture.read()
        if not ok or not math.isfinite(fps) or not 1 <= fps <= 120 or count <= 0 or min(width, height) <= 0:
            raise ValueError("Không đọc được video hoặc thông số video không hợp lệ.")
        if count / fps > 600 or width * height > 3840 * 2160:
            raise ValueError("Chọn clip tối đa 10 phút, độ phân giải tối đa 4K.")
        return dict(fps=fps, frames=count, width=width, height=height, duration_s=count / fps)
    finally:
        capture.release()


def classify_color(feature, centers):
    import numpy as np
    if feature is None or centers is None:
        return "unknown"
    distances = np.linalg.norm(centers - feature, axis=1)
    order = np.argsort(distances)
    if distances[order[0]] > 45 or distances[order[1]] - distances[order[0]] < 8:
        return "unknown"
    return ("A", "B")[int(order[0])]


def analyze(source: Path, folder: Path, progress, cancelled) -> dict:
    config = Path(__file__).resolve().parents[2] / ".tmp/ultralytics"
    config.mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config)
    import cv2
    import numpy as np
    import supervision as sv
    import torch
    from ultralytics import YOLO
    from sklearn.cluster import KMeans
    from backend.cv.team_classifier import jersey_feature
    from backend.cv.track_video import suppress_duplicate_people
    from backend.cv.team_smoother import TrackRoleSmoother
    from backend.cv.pitch_boundary import pitch_region, inside_pitch

    info = video_info(source)
    weights = Path(__file__).resolve().parents[2] / "data/raw/yolo11n.pt"
    if not weights.is_file():
        raise ValueError("Chưa có trọng số YOLO cục bộ data/raw/yolo11n.pt.")
    device = "0" if torch.cuda.is_available() else "cpu"
    image_size = 1280 if device != "cpu" else 640
    model = YOLO(str(weights))
    classes = [key for key, name in model.names.items() if name == "person"]
    if not classes:
        raise ValueError("Trọng số không có lớp person.")
    capture = cv2.VideoCapture(str(source))
    centers = None
    try:
        # Calibration uses at most 12 decoded frames and 300 torso features.
        features = []
        for i, frame_id in enumerate(np.linspace(0, info["frames"] - 1, min(12, info["frames"]), dtype=int)):
            if cancelled():
                raise AnalysisCancelled()
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_id))
            ok, frame = capture.read()
            if ok:
                region = pitch_region(frame)
                result = model.predict(frame, classes=classes, conf=.1, imgsz=image_size, device=device, verbose=False)[0]
                for box in result.boxes.xyxy.cpu().numpy():
                    if not inside_pitch(region, box):
                        continue
                    feature = jersey_feature(frame, box.tolist(), "foreground")
                    if feature is not None and len(features) < 300:
                        features.append(feature)
            progress(stage="Đang ước lượng màu áo", progress=round((i + 1) / 12 * 8, 1), device=device)
        if len(features) >= 10 and len(np.unique(features, axis=0)) >= 2:
            clustering = KMeans(n_clusters=2, random_state=42, n_init=10).fit(np.array(features))
            candidate = clustering.cluster_centers_
            counts = np.bincount(clustering.labels_, minlength=2)
            if np.linalg.norm(candidate[0] - candidate[1]) >= 20 and min(counts) >= 3:
                centers = candidate[np.argsort(candidate[:, 0])]
    finally:
        capture.release()

    tracker = sv.ByteTrack(frame_rate=round(info["fps"]))
    smoother = TrackRoleSmoother(info["fps"])
    capture = cv2.VideoCapture(str(source))
    chunk_frames = max(1, round(info["fps"] * 10))
    frames, chunks, observations = 0, 0, 0
    ids = set()
    chunk = []
    roles_count = {"A": 0, "B": 0, "unknown": 0}
    boundary_frames = excluded = 0
    def flush():
        nonlocal chunks, chunk
        (folder / f"chunk-{chunks}.json").write_text(json.dumps({"frames": chunk}), encoding="utf-8")
        chunks += 1
        chunk = []
    try:
        while True:
            if cancelled():
                raise AnalysisCancelled()
            ok, frame = capture.read()
            if not ok:
                break
            if frames >= math.ceil(info["fps"] * 600) or frame.shape[:2] != (info["height"], info["width"]):
                raise ValueError("Video vượt thời lượng cho phép hoặc đổi kích thước giữa clip.")
            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if abs(timestamp - frames / info["fps"]) > max(.015, .75 / info["fps"]):
                raise ValueError("Nhịp khung hình không đều; hãy xuất lại video với FPS cố định để đồng bộ tracking.")
            result = model.predict(frame, classes=classes, conf=.1, imgsz=image_size, device=device, verbose=False)[0]
            region = pitch_region(frame)
            boundary_frames += region is not None
            candidates = suppress_duplicate_people(sv.Detections.from_ultralytics(result))
            keep = np.array([inside_pitch(region, box) for box in candidates.xyxy], dtype=bool)
            excluded += int((~keep).sum())
            detections = tracker.update_with_detections(candidates[keep])
            # ByteTrack may retain internal lost-track state; publish only a
            # current observation whose foot still passes this frame's boundary.
            detections = detections[np.array([inside_pitch(region, box) for box in detections.xyxy], dtype=bool)]
            smoother.advance(frames)
            boxes = []
            for box, track_id in zip(detections.xyxy, detections.tracker_id):
                role = smoother.update(frames, int(track_id), classify_color(jersey_feature(frame, box.tolist(), "foreground"), centers))
                roles_count[role] += 1
                ids.add(int(track_id))
                boxes.append({"id": int(track_id), "group": role, "xyxy": [round(float(v), 2) for v in box]})
            observations += len(boxes)
            chunk.append({"frame": frames, "time_s": frames / info["fps"], "boxes": boxes,
                          "pitch_boundary": region.round(2).tolist() if region is not None else None})
            frames += 1
            if len(chunk) >= chunk_frames:
                flush()
            if frames % max(1, round(info["fps"])) == 0:
                progress(stage="Đang phát hiện và theo dõi người", progress=min(98, 8 + 90 * frames / info["frames"]), processed_frames=frames, total_frames=info["frames"], device=device)
        if not frames or frames < info["frames"] - max(2, round(info["fps"] * .1)):
            raise ValueError("Video bị lỗi hoặc dừng giải mã trước cuối clip. Hãy xuất lại MP4 H.264.")
        if chunk:
            flush()
    finally:
        capture.release()
    return {**info, "frames": frames, "chunk_frames": chunk_frames, "chunks": chunks,
            "device": device, "image_size": image_size, "confidence": .1, "track_ids": len(ids), "observations": observations,
            "group_observations": roles_count, "color_groups_available": centers is not None,
            "boundary_filter": {"method": "white_touchlines_grass_v1", "frames_with_boundary": boundary_frames,
                                "excluded_detections": excluded, "missing_boundary_policy": "no_tracking"},
            "limitations": ["A/B là nhóm màu áo ước lượng, chưa xác nhận đội, thủ môn hoặc trọng tài.",
                            "Chỉ theo dõi điểm chân trong vùng biên trắng ước lượng; frame không rõ biên bị bỏ. Có thể bỏ sót khi che khuất hoặc góc quay cận.",
                            "Chưa hiệu chỉnh sân: lọc biên ảnh không tạo tọa độ mét, tốc độ hoặc quãng đường.",
                            "ID là mã theo dõi, có thể đổi khi che khuất hoặc chuyển cảnh; không phải số cầu thủ."]}
