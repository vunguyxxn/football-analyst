from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from backend.tactics.review_formation import evaluate_review, main, validate_review


@pytest.fixture
def inputs():
    fixtures = Path(__file__).resolve().parents[1] / "docs/fixtures"
    return tuple(json.loads((fixtures / name).read_text(encoding="utf-8")) for name in
                 ("metrica_formation_windows.json", "metrica_formation_agent_review.json"))


def test_real_draft_agreement_and_unscorable_is_never_true_unknown(inputs):
    result = evaluate_review(*inputs)
    assert result["independent_ground_truth"] is False
    assert result["human_reviewed"] is False
    assert result["review_status_counts"] == {"insufficient_data": 5, "unscorable": 14, "draft_shape": 5}
    assert result["agreement_counts"]["gap"] == {"unassessed": 19, "abstained": 4, "disagrees_with_draft": 1}
    assert result["agreement_counts"]["template"] == {"unassessed": 19, "abstained": 3, "disagrees_with_draft": 2}
    for row in result["windows"]:
        if row["status"] != "draft_shape":
            assert row["gap"]["outcome"] == row["template"]["outcome"] == "unassessed"


@pytest.mark.parametrize("flag", ["human_reviewed", "independent_ground_truth"])
def test_cannot_upgrade_agent_provenance(inputs, flag):
    packet, review = deepcopy(inputs)
    review[flag] = True
    with pytest.raises(ValueError, match="provenance"):
        validate_review(packet, review)


def test_modified_source_packet_is_rejected(inputs):
    packet, review = deepcopy(inputs)
    packet["reports"][1]["teams"][0]["formation_windows"][0]["players"][0]["median_position_m"][0] += 1
    with pytest.raises(ValueError, match="hash"):
        validate_review(packet, review)


@pytest.mark.parametrize("fault", ["duplicate", "missing", "wrong_line", "fake_unknown", "bad_snapshot", "bad_cadence"])
def test_invalid_review_decisions_fail_closed(inputs, fault):
    packet, review = deepcopy(inputs)
    draft = next(row for row in review["rows"] if row["status"] == "draft_shape")
    if fault == "duplicate":
        review["rows"].append(deepcopy(review["rows"][0]))
    elif fault == "missing":
        review["rows"].pop()
    elif fault == "wrong_line":
        draft["lines"][0][0] = 11
    elif fault == "fake_unknown":
        next(r for r in review["rows"] if r["status"] == "unscorable")["shape"] = "unknown"
    elif fault == "bad_snapshot":
        draft["snapshots"][0]["players"][0]["xy_m"][0] = 106
    else:
        draft["snapshots"][0]["frame"] += 1
    with pytest.raises(ValueError):
        validate_review(packet, review)


def test_cli_evaluation_and_preserve_existing_artifacts(tmp_path, monkeypatch):
    output = tmp_path / "review"
    monkeypatch.setattr(sys, "argv", ["review", "--output-dir", str(output)])
    main()
    result = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    assert result["review_status_counts"]["draft_shape"] == 5
    assert "Không phải độ chính xác chiến thuật" in (output / "review.md").read_text(encoding="utf-8")
    before = (output / "evaluation.json").read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert (output / "evaluation.json").read_bytes() == before
