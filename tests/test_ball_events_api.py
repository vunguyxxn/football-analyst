import hashlib
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import video_jobs


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(video_jobs, "ROOT", tmp_path)
    job_id = "e" * 32
    folder = tmp_path / job_id
    folder.mkdir()
    (folder / "source.mp4").write_bytes(b"source")
    video_jobs.write_status(folder, {"id": job_id, "status": "completed", "result": {"frames": 300, "fps": 30}})
    research = folder / "ball_research"
    research.mkdir()
    payload = {"source_sha256": hashlib.sha256(b"source").hexdigest(), "person_job_id": job_id,
               "frames": 300, "confirmed_passes": 999, "shots": 999,
               "possible_passes": [{"kind": "possible_pass", "status": "unverified", "group": "A",
                                    "start_s": 1, "end_s": 2, "from_id": 1, "to_id": 2}]}
    path = research / "report.json"
    return job_id, path, payload


def test_research_events_never_become_confirmed_statistics(tmp_path, monkeypatch):
    job_id, path, payload = fixture(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.get(f"/api/video-jobs/{job_id}/ball-events")
    assert response.json()["status"] == "not_available" and response.json()["confirmed_passes"] is None
    path.write_text(json.dumps(payload))
    body = client.get(f"/api/video-jobs/{job_id}/ball-events").json()
    assert body["status"] == "research_candidates" and len(body["possible_passes"]) == 1
    assert body["confirmed_passes"] is None and body["shots"] is None


def test_research_rejects_wrong_source_wrong_job_or_claimed_confirmed_event(tmp_path, monkeypatch):
    job_id, path, payload = fixture(tmp_path, monkeypatch)
    client = TestClient(app)
    for change in ({"person_job_id": "other"}, {"source_sha256": "other"}, {"frames": 200},
                   {"possible_passes": [{**payload["possible_passes"][0], "status": "confirmed"}]},
                   {"possible_passes": [{**payload["possible_passes"][0], "end_s": 99}]},
                   {"possible_passes": [{**payload["possible_passes"][0], "from_id": 2}]}):
        path.write_text(json.dumps({**payload, **change}))
        assert client.get(f"/api/video-jobs/{job_id}/ball-events").status_code == 422
