import json

import cv2
import numpy as np
import pytest

from backend.cv.team_classifier import JerseyClassifier, jersey_feature, load_samples, evaluate


def calibration():
    # Deliberately place B before A; K-means cluster IDs must not define teams.
    features = np.array([[150, 90, 110], [151, 91, 110],
                         [140, 170, 90], [141, 170, 91],
                         [230, 100, 210], [231, 101, 210]], dtype=float)
    return features, ["B", "B", "A", "A", "referee", "referee"]


def test_calibration_maps_clusters_and_keeps_referee_out_of_teams():
    features, roles = calibration()
    classifier = JerseyClassifier().fit(features, roles)
    assert [classifier.predict_feature(feature) for feature in features] == roles
    assert classifier.predict_feature(np.array([0, 0, 0])) == "unknown"
    assert classifier.predict_feature(None) == "unknown"
    midpoint = (classifier.centers[0] + classifier.centers[1]) / 2
    assert classifier.predict_feature(midpoint) == "unknown"


def test_missing_role_or_indistinguishable_colors_cannot_calibrate():
    features, roles = calibration()
    with pytest.raises(ValueError, match="two calibration"):
        JerseyClassifier().fit(features[:4], roles[:4])
    with pytest.raises(ValueError):
        JerseyClassifier().fit(np.full((6, 3), 100.0), roles)


def test_torso_feature_ignores_grass_head_and_shorts():
    frame = np.full((100, 60, 3), (0, 180, 0), dtype=np.uint8)
    frame[:20] = (0, 0, 255)
    frame[50:] = (255, 0, 0)
    frame[20:50, 12:48] = (200, 50, 180)
    expected = cv2.cvtColor(np.uint8([[[200, 50, 180]]]), cv2.COLOR_BGR2LAB)[0, 0]
    assert jersey_feature(frame, [0, 0, 60, 100]) == pytest.approx(expected)
    assert jersey_feature(frame, [0, 0, 3, 5]) is None
    assert jersey_feature(frame, [300, 300, 400, 400]) is None
    assert jersey_feature(frame, [float("nan"), 0, 60, 100]) is None
    assert jersey_feature(np.full_like(frame, (0, 180, 0)), [0, 0, 60, 100]) is None


def test_annotations_reject_frame_leakage_and_wrong_video(tmp_path):
    path = tmp_path / "samples.json"
    samples = [{"frame": 0, "bbox": [0, 0, 30, 60], "role": "A", "split": "calibration"},
               {"frame": 0, "bbox": [30, 0, 60, 60], "role": "B", "split": "evaluation"}]
    path.write_text(json.dumps({"video": "in.mp4", "samples": samples}))
    with pytest.raises(ValueError, match="disjoint"):
        load_samples(tmp_path / "in.mp4", path)
    with pytest.raises(ValueError, match="does not match"):
        load_samples(tmp_path / "other.mp4", path)


def test_fluorescent_green_shirt_is_not_discarded_as_grass():
    fluorescent = np.full((100, 60, 3), (90, 255, 180), dtype=np.uint8)
    assert jersey_feature(fluorescent, [0, 0, 60, 100]) is not None


def test_same_filename_with_different_video_content_is_rejected(tmp_path):
    source, annotations = tmp_path / "in.mp4", tmp_path / "samples.json"
    source.write_bytes(b"different video")
    annotations.write_text(json.dumps({"video": source.name, "video_sha256": "0"*64, "samples": []}))
    with pytest.raises(ValueError, match="SHA256"):
        load_samples(source, annotations)


def test_video_evaluation_uses_only_calibration_for_mapping(tmp_path):
    source, annotations = tmp_path / "in.mp4", tmp_path / "samples.json"
    colors = {"A": (190, 80, 180), "B": (200, 190, 30), "referee": (10, 240, 220)}
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (180, 100))
    assert writer.isOpened()
    samples = []
    for frame_id in range(3):
        frame = np.zeros((100, 180, 3), dtype=np.uint8)
        for index, (role, color) in enumerate(colors.items()):
            frame[:, index*60:(index+1)*60] = color
            samples.append({"frame": frame_id, "bbox": [index*60, 0, (index+1)*60, 100],
                            "role": role, "split": "calibration" if frame_id < 2 else "evaluation"})
        writer.write(frame)
    writer.release()
    annotations.write_text(json.dumps({"video": source.name, "samples": samples}))
    report = evaluate(source, annotations)
    assert report["accuracy"] == 1
    assert report["evaluation_samples"] == 3
    assert report["referee_recall"] == 1
    # Wrong evaluation labels lower the score, rather than changing the fit.
    samples[-3]["role"] = "B"
    annotations.write_text(json.dumps({"video": source.name, "samples": samples}))
    wrong_report = evaluate(source, annotations)
    assert wrong_report["accuracy"] == pytest.approx(2/3)
    assert wrong_report["predictions"][0]["predicted"] == "A"
