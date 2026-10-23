from copy import deepcopy
import json
import sys

import numpy as np
import pytest

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics import metrica_report
from backend.tactics.metrica_report import player_profile, team_report


def track(speed=2., n=100, track_id=11):
    times = np.arange(n) / 10
    return Trajectory(1, track_id, "A", np.arange(n), times,
                      np.column_stack((10 + speed * times, np.full(n, 34.))),
                      np.zeros(n, dtype=int), 10.)


def test_constant_velocity_has_known_partial_distance_speed_and_heatmap():
    result = player_profile(track(), 0, 10, 11)
    assert result["observed_distance_m"] == pytest.approx(19)
    assert result["represented_motion_duration_s"] == pytest.approx(9.5)
    assert result["observed_continuous_duration_s"] == pytest.approx(9.9)
    assert result["mean_speed_kmh"] == pytest.approx(7.2)
    assert result["max_speed_kmh"] == pytest.approx(7.2)
    assert result["sample_coverage"] == 1
    assert sum(map(sum, result["heatmap_observed_frames"])) == 100
    assert result["is_goalkeeper"]


def test_gap_is_not_bridged_even_when_less_than_one_second():
    t = track()
    keep = (t.frames < 5) | (t.frames >= 10)
    t.frames, t.times, t.xy, t.segments = [a[keep] for a in (t.frames, t.times, t.xy, t.segments)]
    result = player_profile(t, 0, 10, 11)
    assert result["continuity_breaks"] == 1
    assert result["observed_distance_m"] == pytest.approx(17)
    assert result["represented_motion_duration_s"] == pytest.approx(8.5)
    assert result["sample_coverage"] == .95


def test_teleport_rejected_instead_of_clamped():
    t = track()
    t.xy[50:, 0] += 40
    result = player_profile(t, 0, 10, 11)
    assert result["rejected_motion_intervals"] == 1
    assert result["observed_distance_m"] == pytest.approx(18)
    assert result["max_speed_kmh"] == pytest.approx(7.2)
    # Heatmap includes actual observed samples, not just accepted motion intervals.
    assert sum(map(sum, result["heatmap_observed_frames"])) == 100


def test_stationary_and_insufficient_duration_are_distinct():
    stationary = player_profile(track(speed=0), 0, 10, 1)
    assert stationary["mean_speed_kmh"] == stationary["max_speed_kmh"] == 0
    brief = player_profile(track(n=4), 0, 10, 1)
    assert brief["mean_speed_kmh"] is None and brief["max_speed_kmh"] is None
    assert brief["represented_motion_duration_s"] == 0


def test_window_excludes_outside_samples_and_bad_coordinates():
    result = player_profile(track(), 2, 7, 11)
    assert result["samples"] == 50
    assert result["observed_distance_m"] == pytest.approx(9)
    t = track()
    t.xy[0, 0] = float("nan")
    with pytest.raises(ValueError, match="coordinates"):
        player_profile(t, 0, 10, 11)
    with pytest.raises(ValueError, match="no observations"):
        player_profile(track(), 20, 30, 11)


def test_team_report_combines_players_and_quality_guard():
    tracks = [track(track_id=p) for p in range(1, 12)]
    result = team_report(tracks, 0, 10, 5, 11, 1)
    assert len(result["players"]) == 11
    assert result["formation_summary"] == {"total_windows": 2, "observed_shape_windows": 0, "unknown_windows": 2}
    assert result["unprocessed_formation_tail_s"] == 0
    with pytest.raises(ValueError, match="Duplicate"):
        team_report(tracks + [tracks[0]], 0, 10, 5, 11, 1)
    with pytest.raises(ValueError, match="goalkeeper"):
        team_report(tracks, 0, 10, 5, 99, 1)
    mixed = deepcopy(tracks)
    mixed[0].team = "B"
    with pytest.raises(ValueError, match="one nonempty"):
        team_report(mixed, 0, 10, 5, 11, 1)


def test_cli_pinned_sources_provenance_and_no_overwrite(tmp_path, monkeypatch):
    # Real inputs are exercised separately; isolate orchestration with a pinned
    # fixture manifest so CI does not require the large local tracking files.
    import hashlib

    for side in ("Home", "Away"):
        (tmp_path / f"Sample_Game_1_RawTrackingData_{side}_Team.csv").write_bytes(b"fixture")
    original = metrica_report.json.loads
    monkeypatch.setattr(metrica_report.json, "loads", lambda value: {
        "files": [{"filename": f"Sample_Game_1_RawTrackingData_{side}_Team.csv",
                   "sha256": hashlib.sha256(b"fixture").hexdigest()} for side in ("Home", "Away")]})

    def fake_load(path, game, team, start, stop, period):
        tracks = [track(track_id=p) for p in range(1, 12)]
        for t in tracks:
            t.team = team
        return tracks, {"native_frames": 100, "fps": 10}

    monkeypatch.setattr(metrica_report, "load_tracking", fake_load)
    output = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", ["report", "--data-dir", str(tmp_path), "--game", "1",
                                    "--home-goalkeeper", "11", "--away-goalkeeper", "11",
                                    "--home-direction", "1", "--start", "0", "--stop", "10",
                                    "--output", str(output)])
    metrica_report.main()
    report = original(output.read_text(encoding="utf-8"))
    assert len(report["teams"]) == 2
    assert len(report["teams"][1]["players"]) == 11
    assert report["teams"][1]["attack_direction"] == -1
    assert len(report["sources"][0]["sha256"]) == 64
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        metrica_report.main()
    assert output.read_bytes() == before
    output.unlink()
    (tmp_path / "Sample_Game_1_RawTrackingData_Home_Team.csv").write_bytes(b"changed")
    with pytest.raises(SystemExit):
        metrica_report.main()
    assert not output.exists()
