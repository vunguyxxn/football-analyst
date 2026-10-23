import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics import formation_stability as stability


def predictions(shape="4-4-2"):
    return {"status": "observed_shape", "shape": shape}


def tracks():
    fixture = json.loads((Path(__file__).resolve().parents[1] /
                          "docs/fixtures/formation_template_cases.json").read_text(encoding="utf-8"))
    points = fixture["cases"][0]["xy"]
    return [Trajectory(1, p, "A", np.arange(250), np.arange(250) / 25,
                       np.tile(xy, (250, 1)), np.zeros(250, dtype=int), 25.)
            for p, xy in enumerate(points, 1)]


def test_consensus_uses_all_five_slots_and_never_promotes_unknown():
    median = predictions()
    assert stability.assess_stability(median, [predictions()] * 5)["shape"] == "4-4-2"
    accepted = stability.assess_stability(median, [predictions()] * 4 + [{"status": "unknown"}])
    assert accepted["agreement_count"] == 4 and accepted["scheduled_samples"] == 5
    rejected = stability.assess_stability(median, [predictions()] * 3 + [{"status": "unknown"}] * 2)
    assert rejected["reason"] == "insufficient_temporal_support"
    assert stability.assess_stability({"status": "unknown"}, [predictions()] * 5)["reason"] == "median_unknown"
    assert stability.assess_stability(median, [predictions()] * 4 + [None])["reason"] == "missing_temporal_slot"
    with pytest.raises(ValueError):
        stability.assess_stability(median, [predictions()] * 4)


def test_stationary_known_layout_and_snapshot_times():
    result = stability.check_window(tracks(), 0, 10, 11, 1)
    for method in ("gap", "template"):
        assert result["temporal"][method]["shape"] == "4-4-2"
    assert [s["time_s"] for s in result["samples"]] == [1, 3, 5, 7, 9]


def test_transient_layout_rejected_despite_valid_median():
    source = tracks()
    fixture = json.loads((Path(__file__).resolve().parents[1] /
                          "docs/fixtures/formation_template_cases.json").read_text(encoding="utf-8"))
    alternate = fixture["cases"][1]["xy"]
    for t, xy in zip(source, alternate):
        mask = ((t.times >= 2.5) & (t.times < 3.5)) | ((t.times >= 4.5) & (t.times < 5.5)) | ((t.times >= 6.5) & (t.times < 7.5))
        t.xy[mask] = xy
    result = stability.check_window(source, 0, 10, 11, 1)
    for method in ("gap", "template"):
        assert result["median"][method]["shape"] == "4-4-2"
        assert result["temporal"][method]["reason"] == "insufficient_temporal_support"
        assert result["temporal"][method]["agreement_count"] == 2


def test_missing_sample_not_replaced_by_distant_valid_frame():
    source = tracks()
    for t in source:
        keep = (t.times < 4.88) | (t.times > 5.12)
        t.frames, t.times, t.xy, t.segments = [a[keep] for a in (t.frames, t.times, t.xy, t.segments)]
    result = stability.check_window(source, 0, 10, 11, 1)
    assert result["median"]["gap"]["joint_coverage"] > .8
    assert result["samples"][2]["observed"] is False
    assert result["temporal"]["gap"]["reason"] == "missing_temporal_slot"


def test_existing_quality_guard_and_ten_second_protocol():
    result = stability.check_window(tracks()[:-1], 0, 10, 11, 1)
    assert result["samples"] == []
    assert result["temporal"]["gap"]["reason"] == "window_quality_rejected"
    with pytest.raises(ValueError):
        stability.check_window(tracks(), 0, 5, 11, 1)


def test_run_checks_protocol_hashes_and_preserves_existing_output(tmp_path, monkeypatch):
    fixture_dir = tmp_path / "docs/fixtures"
    fixture_dir.mkdir(parents=True)
    protocol = json.loads((Path(__file__).resolve().parents[1] /
                           "docs/fixtures/formation_stability_protocol.json").read_text(encoding="utf-8"))
    protocol["start_s"], protocol["stop_s"] = 0, 10
    protocol["teams"] = protocol["teams"][:1]
    protocol_path = fixture_dir / "formation_stability_protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    raw = tmp_path / "data/raw/metrica"
    raw.mkdir(parents=True)
    filename = "Sample_Game_1_RawTrackingData_Home_Team.csv"
    source = raw / filename
    source.write_bytes(b"fixture")
    manifest = {"files": [{"filename": filename, "sha256": hashlib.sha256(b"fixture").hexdigest()}]}
    (fixture_dir / "metrica_benchmark.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(stability, "load_tracking", lambda *args: (tracks(), {"fps": 25}))
    output = tmp_path / "result.json"
    report = stability.run(tmp_path, output)
    assert report["has_reference_labels"] is False
    assert report["summary"]["gap"]["temporally_supported"] == 1
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        stability.run(tmp_path, output)
    assert output.read_bytes() == before
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        stability.run(tmp_path, tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()
    protocol["minimum_agreeing_samples"] = 3
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    with pytest.raises(ValueError, match="disagree"):
        stability.run(tmp_path, tmp_path / "bad.json")
