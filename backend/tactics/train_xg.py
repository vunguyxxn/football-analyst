"""Train one fixed XGBoost xG baseline and evaluate a held-out tournament."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from backend.tactics.prepare_xg import ROOT, digest, split_matches, workspace
from backend.tactics.xg import FEATURES, calibration_bins, feature_matrix, match_bootstrap, score_probabilities, shot_features


def verify_dataset(dataset, protocol):
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if manifest["protocol"] != protocol or digest(dataset / "shots.csv") != manifest["shots_sha256"]:
        raise ValueError("Dataset hash/protocol mismatch")
    if manifest["inventory_sha256"] != digest(ROOT / "docs/fixtures/xg_source_inventory_v1.json"):
        raise ValueError("Dataset source inventory differs")
    assignments = split_matches(manifest["matches"], protocol)
    shots = pd.read_csv(dataset / "shots.csv")
    if shots.empty or shots.event_id.duplicated().any() or not set(shots.target).issubset({0, 1}):
        raise ValueError("Empty/duplicate shots or invalid labels")
    if any(assignments.get(int(row.match_id)) != row.split for row in shots.itertuples()):
        raise ValueError("Match split leakage/mismatch")
    feature_matrix(shots)
    for split in ("train", "val", "test"):
        group = shots.loc[shots.split.eq(split)]
        if set(group.target) != {0, 1}:
            raise ValueError("Each split needs goals and non-goals")
        score_probabilities(group.target, group.statsbomb_xg)
    return shots, manifest


def predict_events(model_directory, events):
    """Internal inference JSON, explicitly restricted to non-penalty shots."""
    from xgboost import XGBClassifier
    events = list(events)
    directory = workspace(model_directory)
    metadata = json.loads((directory / "model_metadata.json").read_text(encoding="utf-8"))
    if metadata["features"] != list(FEATURES) or digest(directory / "model.json") != metadata["model_sha256"]:
        raise ValueError("Model metadata/hash mismatch")
    rows = []
    for event in events:
        if (event.get("type", {}).get("name") != "Shot" or event.get("period") not in (1, 2, 3, 4)
                or event.get("shot", {}).get("type", {}).get("name") == "Penalty"):
            raise ValueError("Model only supports non-penalty shots in periods 1-4")
        rows.append(shot_features(event))
    if not rows:
        return []
    model = XGBClassifier()
    model.load_model(directory / "model.json")
    probabilities = model.predict_proba(feature_matrix(pd.DataFrame(rows)))[:, 1]
    return [{"event_id": event.get("id"), "xg": float(p)} for event, p in zip(events, probabilities)]


def run(dataset, output, protocol):
    from xgboost import XGBClassifier
    import xgboost
    import sklearn
    dataset, output = workspace(dataset), workspace(output)
    if output.exists():
        raise FileExistsError(output)
    shots, manifest = verify_dataset(dataset, protocol)
    groups = {s: shots.loc[shots.split.eq(s)].reset_index(drop=True) for s in ("train", "val", "test")}
    train, val, test = (groups[s] for s in ("train", "val", "test"))
    model = XGBClassifier(**protocol["model"])
    # Never pass test to eval_set; logloss selects the validation best iteration.
    model.fit(feature_matrix(train), train.target,
              eval_set=[(feature_matrix(val), val.target)], verbose=False)
    output.mkdir(parents=True)
    model.save_model(output / "model.json")
    metadata = {"kind": "xg_model_v1", "features": list(FEATURES), "protocol": protocol,
                "scope": "Non-penalty shots in periods 1-4; no video or future outcome inputs",
                "best_iteration": int(model.best_iteration), "model_sha256": digest(output / "model.json"),
                "dataset_manifest_sha256": digest(dataset / "manifest.json"),
                "versions": {"python": platform.python_version(), "xgboost": xgboost.__version__,
                             "sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__}}
    (output / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    loaded = XGBClassifier()
    loaded.load_model(output / "model.json")
    predictions = {}
    for split, group in groups.items():
        probabilities = model.predict_proba(feature_matrix(group))[:, 1]
        restored = loaded.predict_proba(feature_matrix(group))[:, 1]
        if not np.allclose(probabilities, restored, rtol=0, atol=1e-7):
            raise ValueError("Saved model predictions differ")
        predictions[split] = probabilities
    constant = float(train.target.mean())
    metrics = {}
    for split, group in groups.items():
        candidates = {"xgboost": predictions[split], "statsbomb": group.statsbomb_xg.to_numpy(),
                      "constant_train_goal_rate": np.full(len(group), constant)}
        metrics[split] = {name: {**score_probabilities(group.target, values),
                                 "calibration_bins": calibration_bins(group.target, values)} for name, values in candidates.items()}
    report = {"kind": "xg_evaluation_v1", "metadata": metadata, "dataset_counts": manifest["counts"],
              "excluded": manifest["excluded"], "metrics": metrics,
              "test_paired_match_bootstrap": match_bootstrap(test, predictions["test"], test.statsbomb_xg.to_numpy(),
                                                             protocol["bootstrap_match_replicates"], protocol["seed"]),
              "limitations": ["Small men's international-tournament sample; no domestic/women's/video generalization claim",
                              "StatsBomb model training coverage is unknown; provider reference is not independently retrained",
                              "No freeze-frame defender/keeper context; 105x68m scaling is a fixed convention",
                              "One fixed configuration; validation early stopping only, no test tuning",
                              "Cluster bootstrap covers held-out matches, not model retraining uncertainty"]}
    export = shots[["match_id", "event_id", "split", "target", "statsbomb_xg"]].copy()
    export["xgboost_xg"] = np.nan
    for split in groups:
        export.loc[shots.split.eq(split), "xgboost_xg"] = predictions[split]
    export.to_csv(output / "predictions.csv", index=False, encoding="utf-8")
    report["predictions_sha256"] = digest(output / "predictions.csv")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"counts": report["dataset_counts"], "best_iteration": metadata["best_iteration"],
                      "test": {k: {m: v for m, v in s.items() if m != "calibration_bins"} for k, s in metrics["test"].items()},
                      "bootstrap": report["test_paired_match_bootstrap"]}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.dataset, args.output, json.loads((ROOT / "docs/fixtures/xg_protocol_v1.json").read_text()))
