"""Unsupervised two-team palette with explicit rejection of foreign kit colours.

Rejecting a colour does not establish referee/goalkeeper identity. Unknowns
remain visible but must not contribute to either team's tactical group.
"""
import cv2
import numpy as np
from sklearn.cluster import KMeans


def chroma(features):
    lab = np.clip(np.rint(features), 0, 255).astype(np.uint8).reshape(-1, 1, 3)
    hsv = cv2.cvtColor(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR), cv2.COLOR_BGR2HSV)[:, 0].astype(float)
    angle = hsv[:, 0]*np.pi/90
    strength = hsv[:, 1]*hsv[:, 2]/255
    return np.c_[strength*np.cos(angle), strength*np.sin(angle)]


class TeamPalette:
    method = "lab_two_teams_robust_chroma_rejection_v1"

    def __init__(self):
        self.centers = None
        self.chroma_centers = self.chroma_limits = None

    def fit(self, features):
        data = np.asarray(features, float)
        self.centers = None
        if data.ndim != 2 or data.shape[1] != 3 or len(data) < 10 or not np.isfinite(data).all() or len(np.unique(data, axis=0)) < 2:
            return self
        model = KMeans(n_clusters=2, random_state=42, n_init=10).fit(data)
        counts = np.bincount(model.labels_, minlength=2)
        if min(counts) < 3 or np.linalg.norm(model.cluster_centers_[0]-model.cluster_centers_[1]) < 20:
            return self
        order = np.argsort(model.cluster_centers_[:, 0])
        self.centers = model.cluster_centers_[order]
        centers, limits = [], []
        for index in order:
            points = chroma(data[model.labels_ == index])
            center = np.median(points, axis=0)
            sigma = np.maximum(4., 1.4826*np.median(np.abs(points-center), axis=0))
            centers.append(center)
            limits.append(3*sigma)
        self.chroma_centers, self.chroma_limits = np.asarray(centers), np.asarray(limits)
        return self

    def predict_feature(self, feature):
        if feature is None or self.centers is None:
            return "unknown"
        feature = np.asarray(feature, float)
        if feature.shape != (3,) or not np.isfinite(feature).all():
            return "unknown"
        distances = np.linalg.norm(self.centers-feature, axis=1)
        order = np.argsort(distances)
        nearest = order[0]
        if distances[nearest] > 45 or distances[order[1]]-distances[nearest] < 8:
            return "unknown"
        residual = (chroma(feature[None])[0]-self.chroma_centers[nearest])/self.chroma_limits[nearest]
        if residual @ residual > 1:
            return "unknown"
        return ("A", "B")[nearest]

    def report(self):
        return {"method": self.method, "centers_lab": self.centers.tolist() if self.centers is not None else None,
                "chroma_centers": self.chroma_centers.tolist() if self.centers is not None else None,
                "chroma_limits": self.chroma_limits.tolist() if self.centers is not None else None,
                "foreign_colour_role": "unknown", "semantic_referee_or_goalkeeper_verified": False}
