import json
from pathlib import Path
import sys

import numpy as np
import pytest

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics.evaluate_formation import alignment_stress_fixture, main, synthetic_evaluation
from backend.tactics.formation_aligned import aligned_shape
from backend.tactics.formation_stability import check_window
from backend.tactics.formation_templates import template_shape
from backend.tactics.metrica_report import team_report
from backend.tactics.review_formation import evaluate_review


FIXTURES = Path(__file__).resolve().parents[1] / "docs/fixtures"


def read(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def points(case):
    return {**{i + 1: xy for i, xy in enumerate(case["xy"][:-1])}, 11: case["xy"][-1]}


@pytest.mark.parametrize("index", range(6))
def test_known_lines_mirrored_and_original_coordinates(index):
    case = read("formation_template_cases.json")["cases"][index]
    source = points(case)
    result = aligned_shape(source, 11, 1)
    mirror = {p: [105 - xy[0], 68 - xy[1]] for p, xy in reversed(list(source.items()))}
    mirrored = aligned_shape(mirror, 11, -1)
    assert result["shape"] == mirrored["shape"] == case["expected_shape"]
    assert result["score_margin"] == pytest.approx(mirrored["score_margin"])
    assert [set(line["track_ids"]) for line in result["lines"]] == [set(line["track_ids"]) for line in mirrored["lines"]]
    assert np.allclose(result["centroid_m"], np.mean(list(source.values())[:10], axis=0))


@pytest.mark.parametrize("index", [0, 4, 5])
def test_tilt_and_lateral_shift_resolve_constructed_template_abstentions(index):
    stress = alignment_stress_fixture(read("formation_template_cases.json"), read("formation_alignment_stress.json"))
    case = stress["cases"][index]
    source = points(case)
    assert template_shape(source, 11, 1)["status"] == "unknown"
    assert aligned_shape(source, 11, 1)["shape"] == case["expected_shape"]


def test_invalid_coordinates_missing_player_and_extent_abstain():
    cases = read("formation_template_cases.json")["cases"]
    assert aligned_shape(points(cases[6]), 11, 1)["reason"] == "insufficient_spatial_extent"
    assert aligned_shape(points(cases[7]), 11, 1)["reason"] == "need_eleven_including_goalkeeper"
    source = points(cases[0])
    source[1] = [float("nan"), 30]
    with pytest.raises(ValueError):
        aligned_shape(source, 11, 1)
    with pytest.raises(ValueError):
        aligned_shape(points(cases[0]), 11, 0)


def test_optional_integration_preserves_quality_and_motion():
    source = points(read("formation_template_cases.json")["cases"][0])
    tracks = [Trajectory(1, p, "A", np.arange(250), np.arange(250) / 25,
                         np.tile(xy, (250, 1)), np.zeros(250, dtype=int), 25.) for p, xy in source.items()]
    result = check_window(tracks, 0, 10, 11, 1, include_aligned=True)
    assert result["temporal"]["aligned"]["shape"] == "4-4-2"
    rejected = check_window(tracks[:-1], 0, 10, 11, 1, include_aligned=True)
    assert rejected["temporal"]["aligned"]["reason"] == "window_quality_rejected"
    report = team_report(tracks, 0, 10, 10, 11, 1, formation_method="aligned")
    assert report["formation_windows"][0]["shape"] == "4-4-2"
    assert all(p["observed_distance_m"] == 0 for p in report["players"])
    assert "aligned" not in check_window(tracks, 0, 10, 11, 1)["median"]


def test_review_is_development_evidence_with_provenance_preserved():
    result = evaluate_review(read("metrica_formation_windows.json"),
                             read("metrica_formation_agent_review.json"), include_aligned=True)
    assert result["independent_ground_truth"] is False
    assert result["agreement_counts"]["aligned"] == {
        "unassessed": 19, "disagrees_with_draft": 2, "abstained": 2, "agrees_with_draft": 1}


def test_synthetic_defaults_and_aligned_cli(tmp_path, monkeypatch):
    assert "aligned" not in synthetic_evaluation(read("formation_template_cases.json"))["summaries"]
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--include-aligned", "--output", str(output)])
    main()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert "aligned_policy" in report
    assert report["alignment_stress"]["label_source"] == "constructed_tilt_and_lateral_shift_stress"
    assert report["alignment_stress"]["independent_real_ground_truth"] is False
    assert report["metrica"]["emitted"]["gap"] == 3
    assert report["metrica"]["emitted"]["template"] == 2
