import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import video_jobs
from backend.cv.project_uploaded_job import project_job


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(video_jobs, "ROOT", tmp_path)
    job_id = "c" * 32
    folder = tmp_path / job_id
    folder.mkdir()
    (folder / "source.mp4").write_bytes(b"original video")
    video_jobs.write_status(folder, {"id": job_id, "status": "completed", "result": {"frames": 300, "fps": 30}})
    report = {"person_job_id": job_id, "source_sha256": hashlib.sha256(b"original video").hexdigest(),
              "pitch_m": [105, 68], "origin": "bottom_left", "independently_validated": True}
    path = folder / "pitch_estimate"
    path.mkdir()
    return TestClient(app), job_id, path, report


def test_pitch_absence_not_zero_and_draft_never_becomes_validated(tmp_path, monkeypatch):
    client, job_id, path, report = setup(tmp_path, monkeypatch)
    assert client.get(f"/api/video-jobs/{job_id}/pitch-estimate").json()["status"] == "not_available"
    assert client.get(f"/api/video-jobs/{job_id}/pitch-tracking").status_code == 404
    (path / "report.json").write_text(json.dumps(report))
    body = client.get(f"/api/video-jobs/{job_id}/pitch-estimate").json()
    assert body["status"] == "provisional_estimate" and body["independently_validated"] is False


def test_pitch_rejects_foreign_source_job_or_coordinate_system(tmp_path, monkeypatch):
    client, job_id, path, report = setup(tmp_path, monkeypatch)
    for change in ({"person_job_id": "other"}, {"source_sha256": "other"}, {"pitch_m": [120, 80]}, {"origin": "top_left"}):
        (path / "report.json").write_text(json.dumps({**report, **change}))
        assert client.get(f"/api/video-jobs/{job_id}/pitch-estimate").status_code == 422
        assert client.get(f"/api/video-jobs/{job_id}/pitch-tracking").status_code == 422


def test_pitch_tracking_uses_existing_contract_and_rejects_outside_coordinates(tmp_path, monkeypatch):
    client, job_id, path, report = setup(tmp_path, monkeypatch)
    (path / "report.json").write_text(json.dumps(report))
    row = {"frame": 30, "time_s": 1., "track_id": 2, "team": "A", "x_m": 50., "y_m": 30.}
    (path / "tracking.jsonl").write_text(json.dumps(row) + "\n")
    assert client.get(f"/api/video-jobs/{job_id}/pitch-tracking").json() == [row]
    (path / "tracking.jsonl").write_text(json.dumps({**row, "x_m": 106.}))
    assert client.get(f"/api/video-jobs/{job_id}/pitch-tracking").status_code == 422


def test_projection_rejects_wrong_source_before_creating_output(tmp_path, monkeypatch):
    import backend.cv.project_uploaded_job as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    job = tmp_path / "job"
    job.mkdir()
    (job / "source.mp4").write_bytes(b"source A")
    (job / "status.json").write_text(json.dumps({"status": "completed", "result": {"width": 100, "height": 80}}))
    controls = tmp_path / "controls.json"
    controls.write_text(json.dumps({"source_sha256": "other source", "image_size": [100, 80], "pitch_m": [105, 68]}))
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="differ"):
        project_job(job, controls, output)
    assert not output.exists()
