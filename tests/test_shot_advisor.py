from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from backend.advisor.shot_advisor import build_report, collect_shots, evidence, explain_shots, markdown_report, recommend
from backend.tactics.prepare_xg import ROOT, digest
from backend.tactics.xg import FEATURES, feature_matrix, shot_features


@pytest.fixture
def protocol():
    return json.loads((ROOT / "docs/fixtures/advisor_protocol_v1.json").read_text())


def event(identity="a", team=1, x=108., pressure=False):
    return {"id": identity, "index": 100, "type": {"name": "Shot"}, "period": 1, "minute": 10, "second": 5,
            "team": {"id": team, "name": "Same name"}, "player": {"id": 10, "name": "Some Player"},
            "location": [x, 40.], "under_pressure": pressure,
            "shot": {"type": {"name": "Open Play"}, "body_part": {"name": "Right Foot"}}}


def explained(identity, xg=.04, geometry=-.3, pressure=False, pressure_shap=0.):
    raw = event(identity, pressure=pressure)
    values = dict.fromkeys(FEATURES, 0.)
    values.update(distance_m=geometry, under_pressure=pressure_shap)
    return {"event_id": identity, "xg": xg, "features": shot_features(raw), "shap_log_odds": values}


def test_advisor_collects_without_outcome_xg_and_keeps_team_ids_separate():
    penalty, shootout = event("pen"), event("shootout")
    penalty["shot"]["type"]["name"] = "Penalty"
    shootout["period"] = 5
    teams, rows, excluded = collect_shots([event("a", 1), event("b", 2), penalty, shootout])
    assert len(teams) == 2 and [r["team_id"] for r in rows] == [1, 2]
    assert rows[0]["short_name"] == "Player"
    assert excluded == {"penalty": 1, "non_playing_period": 1}
    with pytest.raises(ValueError, match="unique"):
        collect_shots([event(), event()])


def test_advisor_abstains_on_small_subsets_thresholds_and_no_support(protocol):
    rows = [explained(str(i)) for i in range(4)]
    assert recommend(1, rows, protocol) == ([], "insufficient_data")
    # Values exactly at low-xG boundary are not below the threshold.
    rows += [explained("boundary", xg=.08)]
    cards, status = recommend(1, rows, protocol)
    assert status == "review_suggestions" and cards[0]["evidence"]["subset_shots"] == 4
    rows = [explained(str(i), xg=.04 if i < 2 else .1) for i in range(5)]
    assert recommend(1, rows, protocol) == ([], "no_rule_triggered")
    rows = [explained(str(i), geometry=.3) for i in range(5)]
    assert recommend(1, rows, protocol) == ([], "no_rule_triggered")
    # One negative component cannot justify a net-positive geometry claim.
    for row in rows:
        row["shap_log_odds"].update(distance_m=-.1, angle_rad=.4)
    assert recommend(1, rows, protocol) == ([], "no_rule_triggered")


def test_advisor_evidence_links_exact_subset_and_recomputes_metrics(protocol):
    rows = [explained(str(i), xg=.04 if i < 3 else .1) for i in range(5)]
    cards, _ = recommend(1, rows, protocol)
    card = cards[0]
    assert card["rule"] == "review_low_quality_shots"
    assert card["evidence"]["event_ids"] == ["0", "1", "2"]
    assert card["evidence"] == evidence(rows[:3], 5)
    assert card["evidence"]["fraction"] == .6
    assert card["supporting_features"] == ["distance_m"]
    assert card["evidence"]["mean_shap_log_odds"]["distance_m"] == pytest.approx(-.3)


def test_pressure_and_high_quality_rules_need_matching_shap_sign(protocol):
    rows = [explained(str(i), xg=.2, geometry=.3, pressure=True, pressure_shap=-.1) for i in range(5)]
    cards, _ = recommend(1, rows, protocol)
    assert [c["rule"] for c in cards] == ["review_pressure_support", "review_good_entries"]
    for row in rows:
        row["shap_log_odds"]["under_pressure"] = .1
    assert [c["rule"] for c in recommend(1, rows, protocol)[0]] == ["review_good_entries"]


@pytest.fixture
def model_directory(tmp_path):
    from xgboost import XGBClassifier
    rows = [shot_features(event(str(i), x=118.-i*2)) for i in range(24)]
    matrix = feature_matrix(pd.DataFrame(rows))
    target = np.array([1] * 8 + [0] * 16)
    model = XGBClassifier(n_estimators=20, early_stopping_rounds=3, max_depth=2, min_child_weight=1,
                          learning_rate=.2, n_jobs=1, random_state=42)
    model.fit(matrix, target, eval_set=[(matrix, 1-target)], verbose=False)
    assert model.get_booster().num_boosted_rounds() > model.best_iteration + 1
    model.save_model(tmp_path / "model.json")
    metadata = {"features": list(FEATURES), "model_sha256": digest(tmp_path / "model.json"),
                "best_iteration": model.best_iteration}
    (tmp_path / "model_metadata.json").write_text(json.dumps(metadata))
    return tmp_path


def test_real_shap_uses_best_trees_and_ignores_outcome_provider_and_future(model_directory, protocol):
    from xgboost import XGBClassifier
    original = [event(str(i), x=115-i) for i in range(6)]
    _, rows, _ = collect_shots(original)
    explained_rows, audit = explain_shots(model_directory, rows, protocol)
    model = XGBClassifier()
    model.load_model(model_directory / "model.json")
    expected = model.predict_proba(feature_matrix(pd.DataFrame([r["features"] for r in rows])))[:, 1]
    assert audit["trees_explained"] == model.best_iteration + 1
    assert audit["max_probability_error"] < protocol["probability_tolerance"]
    for item, probability in zip(explained_rows, expected):
        margin = item["base_log_odds"] + sum(item["shap_log_odds"].values())
        assert 1 / (1 + np.exp(-margin)) == pytest.approx(float(probability), abs=1e-6)
    changed = deepcopy(original)
    for item in changed:
        item["shot"].update(outcome={"name": "Goal"}, statsbomb_xg=.99, end_location=[120, 40, 1])
    report_a = build_report(original, 1, model_directory, protocol)
    report_b = build_report(changed, 1, model_directory, protocol)
    assert report_a == report_b
    assert report_a["timing"] == "post_match"
    assert "trận 1" in markdown_report(report_a)


def test_empty_team_report_abstains_and_model_tampering_fails(model_directory, protocol):
    starting = event()
    starting["type"]["name"] = "Starting XI"
    report = build_report([starting], 1, model_directory, protocol)
    assert report["shots"] == [] and report["teams"][0]["status"] == "insufficient_data"
    assert report["teams"][0]["mean_xg"] is None
    assert "Chưa đủ" in markdown_report(report)
    (model_directory / "model.json").write_text("tampered")
    with pytest.raises(ValueError, match="hash"):
        build_report([event()], 1, model_directory, protocol)


def test_shap_reconstruction_guard_fails_closed(model_directory, protocol, monkeypatch):
    import shap
    class BadExplainer:
        expected_value = 0.

        def __init__(self, *args, **kwargs):
            pass

        def shap_values(self, matrix, **kwargs):
            return np.zeros((len(matrix), len(FEATURES)))

    _, rows, _ = collect_shots([event()])
    monkeypatch.setattr(shap, "TreeExplainer", BadExplainer)
    with pytest.raises(ValueError, match="reconstruct"):
        explain_shots(model_directory, rows, protocol)
