"""Clip-specific jersey classification and evaluation on reviewed image boxes.

Boxes here are internal image crops, not shared pitch-coordinate records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import KMeans

ROLES = ("A", "B", "referee", "unknown")


def jersey_feature(frame: np.ndarray, bbox: list[float], feature_mode: str = "chromatic") -> np.ndarray | None:
    """Median Lab of torso pixels, excluding likely green grass.

    Fixed torso fractions avoid heads/shorts. Small crops or crops with too few
    retained pixels are rejected. ``foreground`` retains white/black pixels while the
    default ``chromatic`` preserves the original colored-kit behavior.
    This baseline cannot distinguish green jerseys from
    grass, or a spectator wearing the same jersey as a player.
    """
    if feature_mode not in ("chromatic", "foreground"):
        raise ValueError("Unsupported jersey feature mode")
    if len(bbox) != 4 or not np.isfinite(bbox).all():
        return None
    x1, y1, x2, y2 = map(float, bbox)
    minimum_width, minimum_height = (12, 24) if feature_mode == "chromatic" else (8, 16)
    if x2 - x1 < minimum_width or y2 - y1 < minimum_height:
        return None
    height, width = frame.shape[:2]
    left = max(0, min(width, int(x1 + (x2 - x1) * 0.2)))
    right = max(0, min(width, int(x1 + (x2 - x1) * 0.8)))
    top = max(0, min(height, int(y1 + (y2 - y1) * 0.2)))
    bottom = max(0, min(height, int(y1 + (y2 - y1) * 0.5)))
    if right <= left or bottom <= top:
        return None
    crop = frame[top:bottom, left:right]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = np.ones(hsv.shape[:2], dtype=bool)
    if feature_mode == "chromatic":
        mask &= (hsv[:, :, 1] >= 40) & (hsv[:, :, 2] >= 40)
    # Bright fluorescent jerseys can overlap grass hue. Keep near-clipped
    # highlights rather than removing every green/yellow-green pixel.
    grass = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] >= 40) & (hsv[:, :, 2] < 240)
    if feature_mode == "foreground":
        # Compression/green spill can tint a black shirt green. Do not erase
        # dark pixels just because their unreliable hue resembles the pitch.
        grass &= hsv[:, :, 2] >= 100
    mask &= ~grass
    if np.count_nonzero(mask) < (16 if feature_mode == "chromatic" else 8):
        return None
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    return np.median(lab[mask], axis=0).astype(np.float64)


class JerseyClassifier:
    def __init__(self, max_distance: float = 45, min_margin: float = 5, feature_mode: str = "chromatic"):
        if feature_mode not in ("chromatic", "foreground"):
            raise ValueError("Unsupported jersey feature mode")
        self.feature_mode = feature_mode
        if not np.isfinite([max_distance, min_margin]).all() or max_distance <= 0 or min_margin < 0:
            raise ValueError("Invalid color rejection thresholds")
        self.max_distance = max_distance
        self.min_margin = min_margin
        self.centers: np.ndarray | None = None

    def fit(self, features: np.ndarray, roles: list[str]) -> "JerseyClassifier":
        features = np.asarray(features, dtype=np.float64)
        if features.shape != (len(roles), 3) or not np.isfinite(features).all():
            raise ValueError("Calibration requires finite Lab features of shape (n, 3)")
        if any(role not in ROLES[:3] for role in roles):
            raise ValueError("Calibration roles must be A, B or referee")
        if any(roles.count(role) < 2 for role in ROLES[:3]):
            raise ValueError("Need at least two calibration examples for each team and referee")
        player_mask = np.array([role != "referee" for role in roles])
        players = features[player_mask]
        labels = np.array(roles)[player_mask]
        if len(np.unique(players, axis=0)) < 2:
            raise ValueError("Team calibration colors are identical")
        model = KMeans(n_clusters=2, random_state=42, n_init=10).fit(players)
        # Cluster numbers have no semantic meaning; map them using calibration
        # labels only. Evaluation labels never participate in fitting/mapping.
        assignments = [("A", "B"), ("B", "A")]
        mapping = max(assignments, key=lambda pair: np.mean(np.array(pair)[model.labels_] == labels))
        if np.mean(np.array(mapping)[model.labels_] == labels) < 0.8:
            raise ValueError("Calibration colors do not separate the two teams reliably")
        centers = np.array([
            model.cluster_centers_[mapping.index("A")],
            model.cluster_centers_[mapping.index("B")],
            np.median(features[~player_mask], axis=0),
        ])
        if min(np.linalg.norm(centers[i] - centers[j]) for i in range(3) for j in range(i)) < 15:
            raise ValueError("Team/referee calibration colors are too similar")
        self.centers = centers
        return self

    def predict_feature(self, feature: np.ndarray | None) -> str:
        if self.centers is None:
            raise ValueError("Classifier has not been calibrated")
        if feature is None:
            return "unknown"
        feature = np.asarray(feature, dtype=np.float64)
        if feature.shape != (3,) or not np.isfinite(feature).all():
            return "unknown"
        distances = np.linalg.norm(self.centers - feature, axis=1)
        ordered = np.argsort(distances)
        if distances[ordered[0]] > self.max_distance or distances[ordered[1]] - distances[ordered[0]] < self.min_margin:
            return "unknown"
        return ROLES[int(ordered[0])]

    def predict(self, frame: np.ndarray, bbox: list[float]) -> str:
        return self.predict_feature(jersey_feature(frame, bbox, self.feature_mode))


def load_samples(source: Path, samples_path: Path) -> list[dict]:
    payload = json.loads(samples_path.read_text(encoding="utf-8"))
    if payload.get("video") != source.name:
        raise ValueError("Annotation video name does not match source")
    if payload.get("video_sha256"):
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != payload["video_sha256"]:
                raise ValueError("Annotation video SHA256 does not match source")
    samples = payload.get("samples", [])
    if not samples:
        raise ValueError("Annotation samples are empty")
    seen = set()
    frames = {"calibration": set(), "development": set(), "evaluation": set()}
    for sample in samples:
        frame, bbox = sample["frame"], sample["bbox"]
        if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
            raise ValueError("Sample frame must be a non-negative integer")
        if sample["role"] not in ROLES or sample["split"] not in frames:
            raise ValueError("Invalid annotation role or split")
        if len(bbox) != 4 or not np.isfinite(bbox).all() or bbox[0] < 0 or bbox[1] < 0 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise ValueError("Invalid sample image box")
        key = (frame, tuple(bbox))
        if key in seen:
            raise ValueError("Duplicate annotation box")
        seen.add(key)
        frames[sample["split"]].add(frame)
    if any(frames[left] & frames[right] for left, right in (
        ("calibration", "development"), ("calibration", "evaluation"), ("development", "evaluation")
    )):
        raise ValueError("Calibration, development and evaluation frames must be disjoint")
    return samples


def _sample_features(source: Path, samples: list[dict], feature_mode: str = "chromatic"):
    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open video: {source}")
        for frame_id in sorted({sample["frame"] for sample in samples}):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ok, frame = capture.read()
            if not ok:
                raise ValueError(f"Cannot read annotated frame {frame_id}")
            height, width = frame.shape[:2]
            for sample in samples:
                if sample["frame"] == frame_id:
                    if sample["bbox"][2] > width or sample["bbox"][3] > height:
                        raise ValueError("Annotated box extends beyond frame")
                    yield sample, jersey_feature(frame, sample["bbox"], feature_mode)
    finally:
        capture.release()


def fit_from_samples(source: Path, samples_path: Path) -> JerseyClassifier:
    samples = load_samples(source, samples_path)
    feature_mode = json.loads(samples_path.read_text(encoding="utf-8")).get("feature_mode", "chromatic")
    classifier = JerseyClassifier(feature_mode=feature_mode)
    calibration = [sample for sample in samples if sample["split"] == "calibration"]
    features, roles = [], []
    for sample, feature in _sample_features(source, calibration, feature_mode):
        if feature is None:
            raise ValueError(f"No usable jersey color in calibration frame {sample['frame']}")
        features.append(feature)
        roles.append(sample["role"])
    return classifier.fit(np.array(features), roles)


def evaluate(source: Path, samples_path: Path, split: str = "evaluation") -> dict:
    if split not in ("development", "evaluation"):
        raise ValueError("Only development/evaluation splits can be scored")
    classifier = fit_from_samples(source, samples_path)
    samples = [sample for sample in load_samples(source, samples_path) if sample["split"] == split]
    if not samples:
        raise ValueError("No evaluation samples")
    confusion = {role: {predicted: 0 for predicted in ROLES} for role in ROLES}
    predictions = []
    for sample, feature in _sample_features(source, samples, classifier.feature_mode):
        predicted = classifier.predict_feature(feature)
        confusion[sample["role"]][predicted] += 1
        predictions.append({**sample, "predicted": predicted})
    support = {role: sum(confusion[role].values()) for role in ROLES}
    predicted_support = {role: sum(confusion[actual][role] for actual in ROLES) for role in ROLES}
    correct = sum(confusion[role][role] for role in ROLES)
    team_support = support["A"] + support["B"]
    return {
        "video": source.name, "feature_mode": classifier.feature_mode, "split": split, "evaluation_samples": len(samples),
        "scope": "Jersey classification on annotated boxes; not detection/tracking accuracy",
        "support": support, "confusion_matrix": confusion,
        "precision": {role: confusion[role][role] / predicted_support[role] if predicted_support[role] else None for role in ROLES},
        "recall": {role: confusion[role][role] / support[role] if support[role] else None for role in ROLES},
        "accuracy": correct / len(samples),
        "team_accuracy": (confusion["A"]["A"] + confusion["B"]["B"]) / team_support if team_support else None,
        "referee_recall": confusion["referee"]["referee"] / support["referee"] if support["referee"] else None,
        "predictions": predictions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "evaluation"], default="evaluation")
    args = parser.parse_args()
    if args.report.exists() or args.report.resolve() in (args.source.resolve(), args.samples.resolve()):
        parser.error("Report must be a new file")
    report = evaluate(args.source, args.samples, args.split)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "predictions"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
