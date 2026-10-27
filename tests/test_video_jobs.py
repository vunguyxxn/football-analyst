import json
import threading
import time

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app import video_jobs as jobs
from backend.cv.upload_analysis import AnalysisCancelled, classify_color, video_info


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "ROOT", tmp_path)
    monkeypatch.setattr(jobs, "_slot", threading.Lock())
    monkeypatch.setattr(jobs, "_active", {})
    monkeypatch.setattr(jobs, "video_info", lambda _: {})
    return TestClient(app), tmp_path


def wait_done(client, job_id):
    for _ in range(200):
        status = client.get(f"/api/video-jobs/{job_id}").json()
        if status["status"] not in ("running", "queued") and not jobs._slot.locked():
            return status
        time.sleep(.01)
    raise AssertionError("job did not finish")


def test_upload_json_results_chunk_bounds_and_no_pitch_claim(setup, monkeypatch):
    client, root = setup
    def analyze(source, folder, progress, cancelled):
        assert source.read_bytes() == b"video bytes"
        progress(progress=42, processed_frames=2)
        (folder / "chunk-0.json").write_text(json.dumps({"frames": [{"frame": 0, "boxes": [{"id": 2, "xyxy": [1, 2, 3, 4], "group": "unknown"}]}]}))
        return {"chunks": 1, "frames": 1}
    monkeypatch.setattr(jobs, "analyze", analyze)
    response = client.post("/api/video-jobs", content=b"video bytes")
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert wait_done(client, job_id)["status"] == "completed"
    frame = client.get(f"/api/video-jobs/{job_id}/chunks/0").json()["frames"][0]
    assert "x_m" not in frame["boxes"][0]
    assert client.get(f"/api/video-jobs/{job_id}/chunks/-1").status_code == 404
    assert client.get(f"/api/video-jobs/{job_id}/chunks/1").status_code == 404
    assert client.get("/api/video-jobs/not-a-job").status_code == 404


def test_upload_limit_invalid_video_and_extension_release_slot(setup, monkeypatch):
    client, root = setup
    monkeypatch.setattr(jobs, "MAX_BYTES", 4)
    assert client.post("/api/video-jobs", content=b"12345").status_code == 413
    assert not list(root.iterdir()) and not jobs._slot.locked()
    assert client.post("/api/video-jobs?extension=exe", content=b"x").status_code == 415
    def invalid(_):
        raise ValueError("invalid video")
    monkeypatch.setattr(jobs, "video_info", invalid)
    assert client.post("/api/video-jobs", content=b"x").status_code == 422
    assert not jobs._slot.locked() and not list(root.iterdir())


def test_cancel_busy_result_unavailable_and_failure(setup, monkeypatch):
    client, _ = setup
    def analyze(source, folder, progress, cancelled):
        while not cancelled():
            time.sleep(.005)
        raise AnalysisCancelled()
    monkeypatch.setattr(jobs, "analyze", analyze)
    job_id = client.post("/api/video-jobs", content=b"x").json()["id"]
    assert client.get("/api/video-jobs").json()[0]["id"] == job_id
    assert client.post("/api/video-jobs", content=b"x").status_code == 409
    assert client.get(f"/api/video-jobs/{job_id}/chunks/0").status_code == 409
    assert client.post(f"/api/video-jobs/{job_id}/cancel").json()["cancellation_requested"]
    assert wait_done(client, job_id)["status"] == "cancelled"
    assert client.get("/api/video-jobs").json() == []
    def failure(*args):
        raise RuntimeError("GPU error")
    monkeypatch.setattr(jobs, "analyze", failure)
    job_id = client.post("/api/video-jobs", content=b"x").json()["id"]
    assert "GPU error" in wait_done(client, job_id)["stage"]


def test_restart_marks_unfinished_job_failed(setup):
    client, root = setup
    job_id = "a" * 32
    folder = root / job_id
    folder.mkdir()
    jobs.write_status(folder, {"id": job_id, "status": "running", "progress": 20})
    assert client.get(f"/api/video-jobs/{job_id}").json()["status"] == "failed"


def test_color_rejects_ambiguous_or_distant_features():
    import numpy as np
    centers = np.array([[40, 120, 120], [220, 130, 130]])
    assert classify_color(None, centers) == "unknown"
    assert classify_color(np.array([130, 125, 125]), centers) == "unknown"
    assert classify_color(np.array([42, 122, 120]), centers) == "A"
    assert classify_color(np.array([220, 130, 130]), centers) == "B"
    assert classify_color(np.array([220, 220, 220]), centers) == "unknown"


def test_real_video_validation_rejects_empty_file(tmp_path):
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"bad video")
    with pytest.raises(ValueError):
        video_info(source)
