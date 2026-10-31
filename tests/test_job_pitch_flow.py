import json
import threading
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import video_jobs as jobs
from backend.cv import job_pitch_analysis as pitch
from backend.cv.upload_analysis import AnalysisCancelled


class FixedMotion:
    def __init__(self):
        self.matrix = None
        self.age = 0

    def update(self, frame, boxes, anchor=None):
        if anchor is not None:
            self.matrix = anchor.copy()
            self.age = 0
        else:
            self.age += 1
        return {"status": "tracked" if self.matrix is not None else "lost"}


@pytest.fixture
def clip(tmp_path):
    folder = tmp_path / ("e"*32)
    folder.mkdir()
    source = folder / "source.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 180))
    assert writer.isOpened()
    for _ in range(180):
        writer.write(np.full((180, 320, 3), (30, 140, 30), dtype=np.uint8))
    writer.release()
    boxes = [{"id": i+1, "group": "A", "xyxy": [40+i*40, 60, 55+i*40, 100]} for i in range(4)]
    (folder / "chunk-0.json").write_text(json.dumps({"frames": [{"frame": i, "boxes": boxes} for i in range(180)]}))
    info = {"width": 320, "height": 180, "fps": 30., "frames": 180, "chunks": 1,
            "source_sha256": pitch.digest(source)}
    matrix = np.array([[105/320, 0, 0], [0, -68/180, 68], [0, 0, 1.]])
    return folder, source, info, matrix


def run(clip, **kwargs):
    folder, source, info, matrix = clip
    return pitch.analyze_pitch(source, folder, info, lambda **_: None, kwargs.pop("cancelled", lambda: False),
                               finder_factory=kwargs.pop("finder_factory", lambda: lambda _: matrix),
                               quality=kwargs.pop("quality", lambda *_: {"passed": True}), motion_factory=FixedMotion, **kwargs)


def manual(clip):
    _, _, info, matrix = clip
    world = np.array([[20, 60], [80, 60], [80, 10], [20, 10], [50, 50], [60, 25]], float)
    from backend.cv.pitch_keypoints import project
    return {"frame": 0, "source_sha256": info["source_sha256"],
            "image_points": project(np.linalg.inv(matrix), world).tolist(), "pitch_points": world.tolist()}


def test_auto_flow_publishes_positions_heatmap_and_traceable_tactics(clip):
    state = run(clip)
    assert state["status"] == "ready"
    folder = pitch.pitch_folder(clip[0])
    report, tactics = pitch.read_json(folder / "report.json"), pitch.read_json(folder / "tactics.json")
    rows = [json.loads(line) for line in (folder / "tracking.jsonl").read_text().splitlines()]
    assert len(rows) == report["accepted_positions"] > 600
    assert report["publication"]["tracking_sha256"] == pitch.digest(folder / "tracking.jsonl")
    assert sum(sum(row) for row in report["groups"][0]["heatmap_seconds"]) > 20
    supported = [w for w in tactics["windows"] if w["status"] == "observed_cluster"]
    assert supported and supported[0]["recommendations"][0]["evidence"]
    assert all(0 <= r["x_m"] <= 105 and 0 <= r["y_m"] <= 68 for r in rows)


def test_manual_recovery_uses_heldout_points_without_gpu(clip):
    control = manual(clip)
    pitch.atomic_json(clip[0] / "manual-pitch.json", [control])
    state = run(clip, finder_factory=lambda: pytest.fail("Manual recovery must not load GPU"))
    assert state["status"] == "ready"
    control["image_points"][4][0] += 30
    with pytest.raises(ValueError, match="đối chiếu"):
        pitch.validate_manual(control, clip[2])
    control = manual(clip)
    control["source_sha256"] = "0"*64
    with pytest.raises(ValueError, match="khớp"):
        pitch.validate_manual(control, clip[2])


def test_failed_closing_check_drops_buffer_and_does_not_bridge_gap(clip):
    calls = 0
    def quality(*_):
        nonlocal calls
        calls += 1
        return {"passed": calls != 3}
    run(clip, quality=quality)
    rows = [json.loads(line) for line in (pitch.pitch_folder(clip[0]) / "tracking.jsonl").read_text().splitlines()]
    assert rows and min(r["frame"] for r in rows) >= 60


def test_missing_model_and_cancellation_keep_previous_publication(clip):
    state = run(clip, finder_factory=lambda: None)
    assert state["status"] == "needs_input"
    assert not (clip[0] / "pitch-current.json").exists()
    run(clip)
    pointer = (clip[0] / "pitch-current.json").read_bytes()
    with pytest.raises(AnalysisCancelled):
        run(clip, cancelled=lambda: True)
    assert (clip[0] / "pitch-current.json").read_bytes() == pointer


def test_rejected_manual_anchor_keeps_saved_automatic_coverage(clip):
    first = run(clip)
    pitch.atomic_json(clip[0] / "manual-pitch.json", [manual(clip)])
    calls = 0
    def quality(*_):
        nonlocal calls
        calls += 1
        return {"passed": calls != 1}
    second = run(clip, quality=quality, finder_factory=lambda: pytest.fail("No GPU for recovery"))
    assert second["rejected_manual_frames"] == [0]
    assert second["calibrated_seconds"] == first["calibrated_seconds"]
    assert pitch.read_json(clip[0] / "automatic-pitch.json")["anchors"][0]["frame"] == 0


def test_output_limit_is_explicit_partial_and_keeps_valid_json(clip, monkeypatch):
    monkeypatch.setattr(pitch, "MAX_POSITIONS", 100)
    state = run(clip)
    assert state["status"] == "partial" and "giới hạn" in state["message"]
    selected = pitch.pitch_folder(clip[0])
    rows = [json.loads(line) for line in (selected / "tracking.jsonl").read_text().splitlines()]
    assert len(rows) == 100
    assert pitch.read_json(selected / "report.json")["accepted_positions"] == 100


def test_state_write_error_still_releases_processing_slot(clip, monkeypatch):
    event = threading.Event()
    monkeypatch.setattr(jobs, "_slot", threading.Lock())
    jobs._slot.acquire()
    monkeypatch.setattr(jobs, "_active", {clip[0].name: event})
    monkeypatch.setattr(jobs, "analyze_pitch", lambda *args, **kwargs: {"status": "partial"})
    def disk_error(*_):
        raise OSError("disk write failed")
    monkeypatch.setattr(jobs, "atomic_json", disk_error)
    with pytest.raises(OSError, match="disk write"):
        jobs.recalibrate(clip[0].name, clip[0], clip[2], event, False)
    assert not jobs._slot.locked() and not jobs._active


def test_painted_geometry_rejects_unsupported_projection():
    frame = np.full((680, 1050, 3), (30, 140, 30), dtype=np.uint8)
    matrix = np.array([[.1, 0, 0], [0, -.1, 68], [0, 0, 1.]])
    assert not pitch.projection_quality(frame, matrix)["passed"]
    for x in (165, 525, 885):
        cv2.line(frame, (x, 138), (x, 542), (245, 245, 245), 3)
    for x1, x2 in ((0, 165), (885, 1049)):
        for y in (138, 542):
            cv2.line(frame, (x1, y), (x2, y), (245, 245, 245), 3)
    cv2.line(frame, (525, 0), (525, 679), (245, 245, 245), 3)
    cv2.circle(frame, (525, 340), 92, (245, 245, 245), 3)
    # Edge lines are drawn inside the image; validator ignores the 4px border.
    assert pitch.projection_quality(frame, matrix)["passed"]


def test_api_manual_runs_async_and_preserves_source_binding(clip, monkeypatch):
    folder, source, info, matrix = clip
    monkeypatch.setattr(jobs, "ROOT", folder.parent)
    monkeypatch.setattr(jobs, "_slot", threading.Lock())
    monkeypatch.setattr(jobs, "_active", {})
    jobs.write_status(folder, {"id": folder.name, "status": "completed", "progress": 100, "stage": "tracking", "result": info})
    monkeypatch.setattr(jobs, "analyze_pitch", lambda *args, **kwargs: pitch.analyze_pitch(*args, **kwargs, finder_factory=lambda: None, quality=lambda *_: {"passed": True}, motion_factory=FixedMotion))
    monkeypatch.setattr(jobs, "validate_manual_frame", lambda source, payload, info: pitch.validate_manual(payload, info))
    client = TestClient(app)
    bad = manual(clip)
    bad["source_sha256"] = "0"*64
    assert client.post(f"/api/video-jobs/{folder.name}/calibration", json=bad).status_code == 422
    assert not jobs._slot.locked()
    assert client.post(f"/api/video-jobs/{folder.name}/calibration", json=manual(clip)).status_code == 202
    for _ in range(400):
        status = client.get(f"/api/video-jobs/{folder.name}").json()
        if not jobs._slot.locked():
            break
        time.sleep(.01)
    assert status["workflow"]["calibration"]["status"] == "ready"
    assert status["result"]["pitch_estimate_available"]
    assert client.get(f"/api/video-jobs/{folder.name}/pitch-tracking").status_code == 200
    media = client.get(f"/api/video-jobs/{folder.name}/source", headers={"Range": "bytes=0-15"})
    assert media.status_code == 206 and media.content == source.read_bytes()[:16]
    tactics = client.get(f"/api/video-jobs/{folder.name}/tactics").json()
    assert tactics["windows"][0]["status"] == "observed_cluster"
    pointer, controls = (folder / "pitch-current.json").read_bytes(), (folder / "manual-pitch.json").read_bytes()
    def reject_frame(*_):
        raise ValueError("Mốc chưa bám vạch")
    monkeypatch.setattr(jobs, "validate_manual_frame", reject_frame)
    assert client.post(f"/api/video-jobs/{folder.name}/calibration", json=manual(clip)).status_code == 422
    assert not jobs._slot.locked()
    assert (folder / "manual-pitch.json").read_bytes() == controls
    assert (folder / "pitch-current.json").read_bytes() == pointer
    def until_cancelled(source, folder, info, progress, cancelled, **kwargs):
        while not cancelled():
            time.sleep(.005)
        raise AnalysisCancelled()
    monkeypatch.setattr(jobs, "analyze_pitch", until_cancelled)
    assert client.post(f"/api/video-jobs/{folder.name}/calibration", json=None).status_code == 202
    assert client.get(f"/api/video-jobs/{folder.name}/pitch-tracking").status_code == 200
    assert client.post(f"/api/video-jobs/{folder.name}/cancel").json()["cancellation_requested"]
    for _ in range(200):
        if not jobs._slot.locked():
            break
        time.sleep(.01)
    assert not jobs._slot.locked()
    assert (folder / "pitch-current.json").read_bytes() == pointer
    assert client.get(f"/api/video-jobs/{folder.name}").json()["workflow"]["calibration"]["status"] == "cancelled"
