import copy
import itertools
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import video_jobs
from backend.tactics.partial_formation import rectangular_assignment, fit_snapshot, infer_partial
from backend.tactics.formation_templates import template_points
from backend.tactics.video_tactics import build_report


def positions(n=8, shape="4-4-2"):
    return [{"track_id": i, "x_m": float(x), "y_m": float(y)}
            for i, (x, y) in enumerate((template_points(shape) * [20, 20] + [52.5, 34])[:n])]


def sample():
    rows = [{**p, "frame": frame, "time_s": frame / 10, "team": "A"}
            for frame in range(100) for p in positions()]
    return rows, {"source_sha256": "source", "person_job_id": "job", "segments": [{"segment": 0, "start_s": 0., "end_s": 10.}]}


def test_rectangular_assignment_matches_exhaustive_and_is_injective():
    rng = np.random.default_rng(42)
    for n, m in ((1, 4), (3, 5), (4, 4)):
        cost = rng.normal(size=(n, m))
        score, assignment = rectangular_assignment(cost)
        truth = min(sum(cost[i, j] for i, j in enumerate(order)) for order in itertools.permutations(range(m), n))
        assert score == pytest.approx(truth)
        assert len(set(assignment)) == n
    for invalid in (np.zeros((5, 4)), [[float("nan")]], [], np.zeros((1, 11))):
        with pytest.raises(ValueError):
            rectangular_assignment(invalid)


def test_partial_fit_accepts_missing_players_without_inventing_observations():
    people = positions()
    fits = fit_snapshot(people)
    assert next(fit for fit in fits if fit["shape"] == "4-4-2")["rmse_m"] < 1e-6
    frames = {frame: [{**p, "time_s": frame / 10} for p in people] for frame in (0, 10, 20)}
    result = infer_partial(frames, 10)
    assert result["confidence"] == "low" and len(result["candidates"]) == 3
    for candidate in result["candidates"]:
        assert candidate["observed_players"] == [{"id": p["track_id"], "x_m": p["x_m"], "y_m": p["y_m"]} for p in people]
        assert len(candidate["unseen_slots"]) == candidate["missing_outfield_slots"] == 2
        assert len({item["slot"] for item in candidate["observed_to_slot"]}) == 8
        assert set(item["slot"] for item in candidate["unseen_slots"]).isdisjoint(item["slot"] for item in candidate["observed_to_slot"])
        assert all(slot["status"] == "hypothetical_not_observed" for slot in candidate["unseen_slots"])
    assert fit_snapshot(people[:5]) == []
    assert fit_snapshot([{**p, "x_m": 50.} for p in people]) == []
    with pytest.raises(ValueError):
        fit_snapshot([{**p, "y_m": -1.} for p in people])


def test_partial_fit_checks_both_directions_and_reference_time():
    people = positions(9, "4-2-3-1")
    mirrored = [{**p, "x_m": 105-p["x_m"], "time_s": 3.} for p in people]
    fit = next(item for item in fit_snapshot(mirrored) if item["shape"] == "4-2-3-1")
    assert fit["rmse_m"] == pytest.approx(0)
    assert fit["attack_direction_hypothesis"] == -1
    result = infer_partial({30: mirrored}, 99)
    assert result["shape"] is None  # one instant cannot establish stable shape
    assert all(c["reference_frame"] == 30 and c["reference_time_s"] == 3 for c in result["candidates"])


def test_metrics_heatmap_and_advice_use_observed_simultaneous_positions_only():
    rows, calibration = sample()
    # IDs switch halfway: never stitch across time to construct a larger team.
    for row in rows:
        if row["frame"] >= 50:
            row["track_id"] += 100
    report = build_report(rows, calibration, 10, 100)
    a, b = report["windows"]
    assert a["metrics"]["median_people"] == 8
    assert a["metrics"]["median_depth_m"] == 20
    assert a["metrics"]["median_width_m"] == 40
    assert np.sum(a["heatmap_seconds"]) == pytest.approx(80)  # 8 people * 10s, no unseen slots
    assert sum(a["metrics"]["lane_shares"]) == pytest.approx(1)
    assert b["metrics"] is None and b["heatmap_seconds"] is None and b["recommendations"] == []
    for advice in a["recommendations"]:
        assert advice["condition"] and advice["tradeoff"]
        for evidence in advice["evidence"]:
            actual = a["metrics"][evidence["metric"]]
            if "index" in evidence:
                actual = actual[evidence["index"]]
            assert evidence["value"] == actual
    assert report["independently_validated"] is False


def test_segments_groups_and_short_coverage_are_separate():
    rows, calibration = sample()
    calibration["segments"] = [{"segment": 0, "start_s": 0., "end_s": 5.}, {"segment": 1, "start_s": 5., "end_s": 10.}]
    for row in rows:
        if row["frame"] >= 50:
            row["team"] = "B"
        if row["frame"] == 99:
            row["team"] = "unknown"
    windows = build_report(rows, calibration, 10, 100)["windows"]
    assert [item["status"] for item in windows] == ["observed_cluster", "insufficient_data", "insufficient_data", "insufficient_data"]
    assert windows[3]["support"]["seconds"] == 4.9
    assert np.sum(windows[0]["heatmap_seconds"]) == pytest.approx(40)


@pytest.mark.parametrize("change", ["duplicate", "clock", "outside", "overlap", "uncalibrated"])
def test_reject_corrupt_or_mismatched_geometry(change):
    rows, calibration = sample()
    if change == "duplicate": rows.append(copy.copy(rows[0]))
    if change == "clock": rows[0]["time_s"] = 1
    if change == "outside": rows[0]["x_m"] = 106
    if change == "overlap": calibration["segments"].append({"segment": 1, "start_s": 9., "end_s": 10.})
    if change == "uncalibrated": calibration["segments"][0]["start_s"] = 1.
    with pytest.raises(ValueError):
        build_report(rows, calibration, 10, 100)


def test_tactics_api_not_available_source_bound_and_recomputes_changed_positions(tmp_path, monkeypatch):
    monkeypatch.setattr(video_jobs, "ROOT", tmp_path)
    job = "a" * 32
    folder = tmp_path / job
    folder.mkdir()
    video_jobs.write_status(folder, {"status": "completed", "result": {"source_sha256": "source", "frames": 100, "fps": 10}})
    client = TestClient(app)
    url = f"/api/video-jobs/{job}/tactics"
    assert client.get(url).json()["status"] == "not_available"
    path = folder / "pitch_estimate"
    path.mkdir()
    rows, report = sample()
    report.update(person_job_id=job, pitch_m=[105, 68], origin="bottom_left")
    (path / "report.json").write_text(json.dumps(report))
    def write_rows():
        (path / "tracking.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
    write_rows()
    first = client.get(url).json()
    assert first["windows"][0]["metrics"]["median_people"] == 8
    for row in rows: row["y_m"] += 1
    write_rows()
    second = client.get(url).json()
    assert first["input_sha256"]["positions"] != second["input_sha256"]["positions"]
    assert first["windows"][0]["metrics"]["centroid_m"] != second["windows"][0]["metrics"]["centroid_m"]
    report["source_sha256"] = "foreign"
    (path / "report.json").write_text(json.dumps(report))
    assert client.get(url).status_code == 422
