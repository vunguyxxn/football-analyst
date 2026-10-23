from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from backend.tactics import prepare_xg, train_xg
from backend.tactics.xg import FEATURES, calibration_bins, match_bootstrap, score_probabilities, shot_features


def shot(identity="a", x=108., y=40., outcome="Goal"):
    return {"id": identity, "type": {"name": "Shot"}, "period": 1, "location": [x, y],
            "shot": {"type": {"name": "Open Play"}, "body_part": {"name": "Right Foot"},
                     "outcome": {"name": outcome}, "statsbomb_xg": .2}}


def test_xg_geometry_and_no_outcome_provider_or_identity_leakage():
    event = shot()
    features = shot_features(event)
    assert features["distance_m"] == pytest.approx(10.5)
    assert features["angle_rad"] == pytest.approx(2 * np.arctan(3.66 / 10.5))
    assert features["lateral_m"] == 0 and list(features) == list(FEATURES)
    changed = deepcopy(event)
    changed.update(id="different", player={"name": "other"}, team={"name": "other"})
    changed["shot"].update(outcome={"name": "Saved"}, statsbomb_xg=.99, end_location=[120, 40, 1])
    assert shot_features(changed) == features
    assert shot_features(shot(y=30)) == shot_features(shot(y=50))
    assert np.isfinite(list(shot_features(shot(x=120)).values())).all()


@pytest.mark.parametrize("location", [[121, 40], [100, -1], [float("nan"), 40], []])
def test_xg_bad_geometry_is_rejected(location):
    event = shot()
    event["location"] = location
    with pytest.raises(ValueError):
        shot_features(event)


def test_shot_extraction_excludes_penalties_shootouts_and_nonshots():
    penalty, shootout, nonshot = shot("pen"), shot("shootout"), shot("pass")
    penalty["shot"]["type"]["name"] = "Penalty"
    shootout["period"] = 5
    nonshot["type"]["name"] = "Pass"
    rows, excluded = prepare_xg.extract_shots([shot(), penalty, shootout, nonshot], {"match_id": 1}, "train")
    assert len(rows) == 1 and rows[0]["target"] == 1 and rows[0]["x_m"] == 94.5
    assert excluded == {"penalty": 1, "non_playing_period": 1}
    with pytest.raises(ValueError, match="outcome"):
        prepare_xg.extract_shots([shot(outcome="new outcome")], {"match_id": 1}, "train")


def test_match_partition_is_reproducible_disjoint_and_temporal():
    protocol = {"seed": 42, "validation_match_fraction": .2, "development_competitions": [[43, 3]], "test_competitions": [[43, 106]]}
    matches = [{"match_id": i, "match_date": "2018-07-01", "competition_id": 43, "season_id": 3} for i in range(10)]
    matches += [{"match_id": 20, "match_date": "2022-12-01", "competition_id": 43, "season_id": 106}]
    assignments = prepare_xg.split_matches(matches, protocol)
    assert assignments == prepare_xg.split_matches(list(reversed(matches)), protocol)
    assert assignments[20] == "test" and list(assignments.values()).count("val") == 2
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_xg.split_matches(matches + [matches[0]], protocol)
    matches[-1]["match_date"] = "2017-01-01"
    with pytest.raises(ValueError, match="later"):
        prepare_xg.split_matches(matches, protocol)


def test_probability_metrics_calibration_and_paired_cluster_bootstrap():
    result = score_probabilities([0, 1], [.2, .8])
    assert result["roc_auc"] == 1 and result["brier"] == pytest.approx(.04)
    assert score_probabilities([1, 1], [.7, .9])["roc_auc"] is None
    with pytest.raises(ValueError):
        score_probabilities([0, 1], [.1, float("nan")])
    bins = calibration_bins([0, 1], [0., 1.])
    assert bins[0]["shots"] == bins[-1]["shots"] == 1
    assert sum(b["shots"] for b in bins) == 2
    test = pd.DataFrame({"match_id": [1, 1, 2, 2], "target": [0, 1, 0, 1]})
    values = np.array([.1, .8, .2, .7])
    bootstrap = match_bootstrap(test, values, values, 20, 42)
    assert bootstrap == match_bootstrap(test, values, values, 20, 42)
    assert all(v["percentile_95"] == [0., 0.] for v in bootstrap.values())


def test_xg_training_save_reload_inference_and_tamper_guard(tmp_path, monkeypatch):
    original_root = prepare_xg.ROOT
    protocol = json.loads((original_root / "docs/fixtures/xg_protocol_v1.json").read_text())
    protocol["model"].update(n_estimators=15, early_stopping_rounds=3, min_child_weight=1)
    protocol["bootstrap_match_replicates"] = 5
    monkeypatch.setattr(prepare_xg, "ROOT", tmp_path)
    monkeypatch.setattr(train_xg, "ROOT", tmp_path)
    inventory = tmp_path / "docs/fixtures/xg_source_inventory_v1.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("{}")
    matches = [{"match_id": i, "match_date": "2018-07-01", "competition_id": 43, "season_id": 3} for i in range(10)]
    matches += [{"match_id": i, "match_date": "2022-12-01", "competition_id": 43, "season_id": 106} for i in range(20, 24)]
    assignments = prepare_xg.split_matches(matches, protocol)
    rows = []
    for match in matches:
        events = [shot(f"{match['match_id']}-{j}", x=115-j*5, outcome="Goal" if j < 2 else "Saved") for j in range(6)]
        rows.extend(prepare_xg.extract_shots(events, match, assignments[match["match_id"]])[0])
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    pd.DataFrame(rows).to_csv(dataset / "shots.csv", index=False)
    manifest = {"protocol": protocol, "shots_sha256": prepare_xg.digest(dataset / "shots.csv"),
                "inventory_sha256": prepare_xg.digest(inventory), "matches": matches, "counts": {}, "excluded": {}}
    (dataset / "manifest.json").write_text(json.dumps(manifest))
    report = train_xg.run(dataset, tmp_path / "model", protocol)
    assert report["metrics"]["test"]["xgboost"]["shots"] == 24
    result = train_xg.predict_events(tmp_path / "model", [shot()])
    assert result[0]["event_id"] == "a" and 0 <= result[0]["xg"] <= 1
    event = shot()
    event["shot"]["type"]["name"] = "Penalty"
    with pytest.raises(ValueError, match="non-penalty"):
        train_xg.predict_events(tmp_path / "model", [event])
    # Updating CSV+its hash cannot authorize cross-split match leakage.
    data = pd.read_csv(dataset / "shots.csv")
    data.loc[0, "split"] = "test"
    data.to_csv(dataset / "shots.csv", index=False)
    with pytest.raises(ValueError, match="hash/protocol"):
        train_xg.verify_dataset(dataset, protocol)
    manifest["shots_sha256"] = prepare_xg.digest(dataset / "shots.csv")
    (dataset / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="split"):
        train_xg.verify_dataset(dataset, protocol)
    (tmp_path / "model/model.json").write_text("tampered")
    with pytest.raises(ValueError, match="hash"):
        train_xg.predict_events(tmp_path / "model", [shot()])
