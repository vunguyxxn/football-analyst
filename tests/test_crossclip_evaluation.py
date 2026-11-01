import json

import pytest

from backend.cv.evaluate_crossclip_uploads import evaluate_job
from backend.cv.job_pitch_analysis import atomic_json, digest


@pytest.fixture
def job(tmp_path):
    folder = tmp_path / ("a"*32)
    folder.mkdir()
    (folder / "source.mp4").write_bytes(b"pinned local source")
    source_hash = digest(folder / "source.mp4")
    info = {"frames": 16, "fps": 30., "width": 1920, "height": 1080, "chunks": 1, "source_sha256": source_hash}
    atomic_json(folder / "status.json", {"status": "completed", "result": info})
    atomic_json(folder / "calibration-status.json", {"status": "needs_input"})
    frames = []
    for frame in range(16):
        # Both arbitrary colour clusters remain stable, while one identity
        # changes tracker ID. Referee contamination must be reported too.
        boxes = [{"id": 1 if frame < 15 else 99, "group": "B", "xyxy": [80, 30, 120, 100]},
                 {"id": 2, "group": "A", "xyxy": [280, 30, 320, 100]},
                 {"id": 3, "group": "A", "xyxy": [480, 30, 520, 100]}]
        if frame == 15:
            boxes[0]["group"] = "A"  # Heldout error must not remap colour labels.
        frames.append({"frame": frame, "boxes": boxes})
    atomic_json(folder / "chunk-0.json", {"frames": frames})
    clip = {"name": "fixture", "source_sha256": source_hash, "info": info, "checkpoints": []}
    people = [{"identity": "W", "role": "white", "xy": [100, 100]},
              {"identity": "O", "role": "opponent", "xy": [300, 100]},
              {"identity": "R", "role": "referee", "xy": [500, 100]}]
    labels = {"source_sha256": source_hash, "frames": [{"frame": f, "people": people} for f in (0, 15)]}
    return folder, clip, labels


def test_missing_calibration_is_not_counted_as_analysis_success_and_review_catches_errors(job):
    folder, clip, labels = job
    result = evaluate_job(folder, clip, labels, [35])
    assert result["calibrated_seconds"] == result["tactical_windows"] == result["recommendation_items"] == 0
    assert result["pitch_audit"] is None
    review = result["sparse_reviews"][0]
    assert review["first_sample_colour_mapping"] == {"white": "B", "opponent": "A"}
    assert review["heldout_sample_role_matches"] == 2 and review["heldout_sample_role_correct"] == 1
    assert review["sampled_identity_pairs"] == 2
    assert review["apparent_sampled_id_changes"] == [{"identity": "W", "from": 1, "to": 99}]
    assert review["referee_in_team_groups"] == 2


def test_review_rejects_mismatched_source_and_incomplete_job(job):
    folder, clip, labels = job
    labels["source_sha256"] = "0"*64
    with pytest.raises(ValueError, match="source hashes"):
        evaluate_job(folder, clip, labels, [35])
    labels["source_sha256"] = clip["source_sha256"]
    state = json.loads((folder / "status.json").read_text())
    state["status"] = "running"
    atomic_json(folder / "status.json", state)
    with pytest.raises(ValueError, match="completed"):
        evaluate_job(folder, clip, labels, [35])


def test_invented_advice_without_supported_window_is_flagged(job):
    folder, clip, labels = job
    output = folder / "pitch_estimate"
    output.mkdir()
    atomic_json(output / "tactics.json", {"windows": [{"status": "insufficient_data", "recommendations": [{"id": "invented"}]}]})
    result = evaluate_job(folder, clip, labels, [35])
    assert result["tactics_trace_errors"] == ["Advice without a supported observed cluster"]
