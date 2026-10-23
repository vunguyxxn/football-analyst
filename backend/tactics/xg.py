"""Pre-shot expected-goals baseline; no outcome/provider xG in features."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from backend.common.pitch import statsbomb_to_pitch

FEATURES = ("distance_m", "angle_rad", "lateral_m", "is_header", "is_other_body",
            "is_free_kick", "first_time", "under_pressure")
OUTCOMES = {"Blocked", "Goal", "Off T", "Post", "Saved", "Wayward", "Saved Off Target", "Saved to Post"}


def shot_features(event):
    location = event.get("location")
    if not isinstance(location, list) or len(location) < 2:
        raise ValueError("Shot needs a location")
    x, y = map(float, location[:2])
    if not math.isfinite(x + y) or not 0 <= x <= 120 or not 0 <= y <= 80:
        raise ValueError("Shot location outside StatsBomb pitch")
    shot = event["shot"]
    body = shot.get("body_part", {}).get("name")
    kind = shot.get("type", {}).get("name")
    if not body or not kind:
        raise ValueError("Shot needs body part and type")
    first, pressure = shot.get("first_time", False), event.get("under_pressure", False)
    if not isinstance(first, bool) or not isinstance(pressure, bool):
        raise ValueError("Shot flags must be booleans")
    xm, ym = statsbomb_to_pitch(x, y)
    dx, dy = 105 - xm, ym - 34
    angle = math.atan2(7.32 * dx, dx * dx + dy * dy - (7.32 / 2) ** 2)
    return {"distance_m": math.hypot(dx, dy), "angle_rad": angle, "lateral_m": abs(dy),
            "is_header": int(body == "Head"), "is_other_body": int(body not in ("Head", "Left Foot", "Right Foot")),
            "is_free_kick": int(kind == "Free Kick"), "first_time": int(first), "under_pressure": int(pressure)}


def feature_matrix(shots):
    matrix = shots.loc[:, list(FEATURES)].astype(float)
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Non-finite xG features")
    return matrix


def score_probabilities(y, probabilities):
    y, probabilities = np.asarray(y), np.asarray(probabilities, dtype=float)
    if len(y) == 0 or set(np.unique(y)) - {0, 1} or y.shape != probabilities.shape:
        raise ValueError("Need equally sized binary labels and probabilities")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Invalid xG probability")
    return {"roc_auc": float(roc_auc_score(y, probabilities)) if len(np.unique(y)) == 2 else None,
            "brier": float(brier_score_loss(y, probabilities)),
            "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
            "shots": len(y), "goals": int(y.sum()), "mean_prediction": float(probabilities.mean())}


def calibration_bins(y, probabilities):
    y, probabilities = np.asarray(y), np.asarray(probabilities)
    bins = []
    for i in range(10):
        selected = (probabilities >= i / 10) & (probabilities < (i + 1) / 10 if i < 9 else probabilities <= 1)
        bins.append({"lower": i / 10, "upper": (i + 1) / 10, "shots": int(selected.sum()),
                     "mean_prediction": float(probabilities[selected].mean()) if selected.any() else None,
                     "goal_rate": float(y[selected].mean()) if selected.any() else None})
    return bins


def match_bootstrap(test, probabilities, baseline, repeats, seed):
    """Paired cluster bootstrap; preserve dependence between shots in a match."""
    rng = np.random.default_rng(seed)
    groups = [g.index.to_numpy() for _, g in test.reset_index(drop=True).groupby("match_id", sort=True)]
    y = test.target.to_numpy()
    values = {"roc_auc_delta": [], "brier_delta": []}
    for _ in range(repeats):
        indices = np.concatenate([groups[i] for i in rng.integers(0, len(groups), size=len(groups))])
        a, b = score_probabilities(y[indices], probabilities[indices]), score_probabilities(y[indices], baseline[indices])
        if a["roc_auc"] is not None:
            values["roc_auc_delta"].append(a["roc_auc"] - b["roc_auc"])
        values["brier_delta"].append(a["brier"] - b["brier"])
    return {key: {"replicates": len(v), "percentile_95": np.quantile(v, [.025, .975]).tolist() if v else None}
            for key, v in values.items()}
