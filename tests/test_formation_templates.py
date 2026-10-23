from itertools import permutations
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics.evaluate_formation import compare_metrica_reports, main, synthetic_evaluation
from backend.tactics.formation import analyze_window
from backend.tactics.formation_templates import minimum_assignment, template_shape


FIXTURES = Path(__file__).resolve().parents[1] / "docs/fixtures"


def cases():
    return json.loads((FIXTURES / "formation_template_cases.json").read_text(encoding="utf-8"))


def points(case):
    return {**{i + 1: xy for i, xy in enumerate(case["xy"][:-1])}, 11: case["xy"][-1]}


def test_assignment_is_exact_against_brute_force_and_not_greedy():
    rng = np.random.default_rng(37)
    for _ in range(20):
        cost = rng.uniform(0, 10, (4, 4))
        score, assignment = minimum_assignment(cost)
        exact = min(sum(cost[i, p[i]] for i in range(4)) for p in permutations(range(4)))
        assert score == pytest.approx(exact)
        assert len(set(assignment)) == 4
        assert sum(cost[i, p] for i, p in enumerate(assignment)) == pytest.approx(score)
    with pytest.raises(ValueError):
        minimum_assignment(np.zeros((2, 3)))


@pytest.mark.parametrize("case_index", range(6))
def test_hand_constructed_layouts_and_mirrored_order(case_index):
    case = cases()["cases"][case_index]
    source = points(case)
    first = template_shape(source, 11, 1)
    mirrored = {p: [105 - xy[0], 68 - xy[1]] for p, xy in reversed(list(source.items()))}
    second = template_shape(mirrored, 11, -1)
    assert first["shape"] == second["shape"] == case["expected_shape"]
    assert first["score_margin"] == pytest.approx(second["score_margin"])
    assert set(p for line in first["lines"] for p in line["track_ids"]) == set(range(1, 11))
    assert [set(v["track_ids"]) for v in first["lines"]] == [set(v["track_ids"]) for v in second["lines"]]
    assert first["candidates"] == sorted(first["candidates"], key=lambda c: c["normalized_rmse"])


def test_unknowns_invalid_input_and_margin_abstention():
    all_cases = cases()["cases"]
    assert template_shape(points(all_cases[6]), 11, 1)["reason"] == "insufficient_spatial_extent"
    assert template_shape(points(all_cases[7]), 11, 1)["reason"] == "need_eleven_including_goalkeeper"
    source = points(all_cases[0])
    assert template_shape(source, 11, 1, minimum_margin=10)["reason"] == "ambiguous_templates"
    source[1] = [float("nan"), 30]
    with pytest.raises(ValueError):
        template_shape(source, 11, 1)
    with pytest.raises(ValueError):
        template_shape(points(all_cases[0]), 11, 0)


def test_template_keeps_existing_window_quality_guard():
    source = points(cases()["cases"][0])
    tracks = [Trajectory(1, p, "A", np.arange(100), np.arange(100) / 10,
                         np.tile(xy, (100, 1)), np.zeros(100, dtype=int), 10.)
              for p, xy in source.items()]
    assert analyze_window(tracks, 0, 10, 11, 1, method="template")["shape"] == "4-4-2"
    assert analyze_window(tracks[:-1], 0, 10, 11, 1, method="template")["status"] == "unknown"
    assert analyze_window(tracks, 0, 15, 11, 1, method="template")["reason"] == "insufficient_joint_coverage"
    with pytest.raises(ValueError):
        analyze_window(tracks, 0, 10, 11, 1, method="invalid")


def test_synthetic_evaluation_provenance_and_abstentions():
    result = synthetic_evaluation(cases())
    assert result["independent_real_ground_truth"] is False
    for summary in result["summaries"].values():
        assert summary["total_cases"] == 72
        assert summary["emitted"] + summary["abstained"] == 72
        assert sum(c["count"] for c in summary["confusion"]) == 72
        assert summary["false_emits_on_unknown_cases"] == 0
    assert result == synthetic_evaluation(cases())


def test_frozen_metrica_unlabeled_and_no_duplicate_windows():
    fixture = json.loads((FIXTURES / "metrica_formation_windows.json").read_text(encoding="utf-8"))
    assert fixture["independent_ground_truth"] is False
    assert all(w["reference"]["label_status"] == "unreviewed" and w["reference"]["shape"] is None
               for r in fixture["reports"] for t in r["teams"] for w in t["formation_windows"])
    result = compare_metrica_reports(fixture["reports"])
    assert result["has_reference_labels"] is False
    assert result["total_windows"] == 24
    assert result["emitted"] == {"gap": 3, "template": 2}
    with pytest.raises(ValueError, match="Duplicate"):
        compare_metrica_reports(fixture["reports"] * 2)


def test_cli_offline_and_no_overwrite(tmp_path, monkeypatch):
    output = tmp_path / "evaluation.json"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--output", str(output)])
    main()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["metrica"]["total_windows"] == 24
    assert len(result["fixture_sha256"]) == 64
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert output.read_bytes() == before
