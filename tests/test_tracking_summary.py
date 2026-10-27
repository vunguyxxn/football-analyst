import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import video_jobs
from backend.cv.tracking_summary import summarize


def write_chunks(folder, frames):
    for index, rows in enumerate([frames[:2], frames[2:]]):
        (folder / f"chunk-{index}.json").write_text(json.dumps({"frames": rows}))


def test_summary_uses_all_frames_keeps_gaps_and_denominators(tmp_path):
    # 4 frames at 2 FPS: two objects initially, empty middle frame,
    # one ID returning. A span must not be counted as continuous observation.
    frames = [
        {"frame": 0, "boxes": [{"id": 1, "group": "A"}, {"id": 2, "group": "B"}]},
        {"frame": 1, "boxes": [{"id": 1, "group": "unknown"}]},
        {"frame": 2, "boxes": []},
        {"frame": 3, "boxes": [{"id": 1, "group": "B"}]},
    ]
    write_chunks(tmp_path, frames)
    result = {"fps": 2, "frames": 4, "chunks": 2, "width": 640, "height": 360}
    summary = summarize(tmp_path, result)
    assert summary["duration_s"] == 2
    assert summary["average_people"] == 1
    assert summary["maximum_people"] == 2
    assert summary["frames_with_people"] == 3
    assert summary["track_ids"] == 2
    assert summary["short_track_ids"] == 1
    assert summary["unknown_fraction"] == .25
    assert summary["tracks"][0] == {"id": 1, "group": "unknown", "frames": 3, "observed_s": 1.5, "first_s": 0, "last_s": 1.5, "missing_s": .5}
    assert [point["average_people"] for point in summary["timeline"]] == [1.5, .5]
    assert sum(group["average_people"] for group in summary["groups"]) == summary["average_people"]
    write_chunks(tmp_path, [{**frame, "boxes": []} for frame in frames])
    empty = summarize(tmp_path, result)
    assert empty["unknown_fraction"] is None
    assert empty["tracks"] == [] and empty["average_people"] == 0


def test_summary_rejects_missing_frames_and_duplicate_ids(tmp_path):
    result = {"fps": 2, "frames": 1, "chunks": 2, "width": 640, "height": 360}
    write_chunks(tmp_path, [{"frame": 1, "boxes": []}])
    with pytest.raises(ValueError):
        summarize(tmp_path, result)
    write_chunks(tmp_path, [{"frame": 0, "boxes": [{"id": 1, "group": "A"}] * 2}])
    with pytest.raises(ValueError):
        summarize(tmp_path, result)
    write_chunks(tmp_path, [{"frame": 0, "boxes": []}])
    with pytest.raises(ValueError):
        summarize(tmp_path, {**result, "frames": 2})


def test_summary_api_works_for_preexisting_completed_job(tmp_path, monkeypatch):
    monkeypatch.setattr(video_jobs, "ROOT", tmp_path)
    job_id = "b" * 32
    folder = tmp_path / job_id
    folder.mkdir()
    write_chunks(folder, [{"frame": 0, "boxes": [{"id": 1, "group": "A"}]}])
    status = {"id": job_id, "status": "completed", "result": {"fps": 1, "frames": 1, "chunks": 2, "width": 640, "height": 360}}
    video_jobs.write_status(folder, status)
    client = TestClient(app)
    response = client.get(f"/api/video-jobs/{job_id}/summary")
    assert response.status_code == 200
    assert response.json()["observations"] == 1
    assert "x_m" not in response.text
    (folder / "chunk-0.json").unlink()
    assert client.get(f"/api/video-jobs/{job_id}/summary").status_code == 422
    status["status"] = "cancelled"
    video_jobs.write_status(folder, status)
    assert client.get(f"/api/video-jobs/{job_id}/summary").status_code == 409
