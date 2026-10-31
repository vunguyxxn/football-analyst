import hashlib
import json

import numpy as np
import pytest

from backend.cv.pitch_keypoints import FitPolicy, PITCH_POINTS, check_landmarks, fit_pitch, project
from backend.cv.evaluate_pitch_keypoints import inputs
from backend.cv import evaluate_pitch_keypoints as evaluator


FORWARD = np.array([[10., 1., 100.], [0.2, -8., 800.], [0.001, 0.0005, 1.]])


def observations():
    return project(FORWARD, PITCH_POINTS), np.ones(32)


def test_geometry_preserves_regulation_markings_and_bottom_left():
    assert PITCH_POINTS[0].tolist() == [0, 68]
    assert PITCH_POINTS[5].tolist() == [0, 0]
    assert PITCH_POINTS[9].tolist() == [16.5, 54.16]
    assert PITCH_POINTS[21].tolist() == [94, 34]
    assert PITCH_POINTS[30].tolist() == [43.35, 34]
    xy, confidence = observations()
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["status"] == "candidate"
    recovered = project(np.array(fit["matrix"]), xy)
    np.testing.assert_allclose(recovered, PITCH_POINTS, atol=1e-4)


def test_ransac_rejects_bad_point_without_moving_others():
    xy, confidence = observations()
    xy[21] += [140, 70]
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["status"] == "candidate"
    assert 21 not in fit["inlier_indices"]
    np.testing.assert_allclose(project(np.array(fit["matrix"]), xy[:20]), PITCH_POINTS[:20], atol=1e-4)


def test_low_confidence_nonfinite_and_out_of_frame_points_are_excluded():
    xy, confidence = observations()
    xy[0] = [np.nan, 5]
    xy[1] = [-1, 5]
    confidence[2] = 0.59
    confidence[3] = np.inf
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["status"] == "candidate"
    assert all(i not in fit["point_indices"] for i in range(4))


def test_sparse_collinear_and_duplicate_points_fail_closed():
    xy, confidence = observations()
    confidence[5:] = 0
    assert fit_pitch(xy, confidence, (1920, 1080))["reason"] == "insufficient_points"
    confidence[:] = 0
    confidence[:6] = 1  # Six points on a goal line, not sufficient geometry.
    assert fit_pitch(xy, confidence, (1920, 1080))["reason"] == "insufficient_coverage"
    confidence[:] = 1
    xy[0] = xy[1]
    assert fit_pitch(xy, confidence, (1920, 1080))["reason"] == "duplicate_image_points"


def test_inconsistent_model_points_do_not_get_identity_fallback():
    xy, confidence = observations()
    xy += np.random.default_rng(13).normal(0, 35, xy.shape)
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["status"] == "rejected"
    assert fit["matrix"] is None


def test_confident_self_consistency_can_still_fail_external_check():
    xy, confidence = observations()
    xy += [30, 0]  # A coherent but incorrect predicted field.
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["status"] == "candidate"
    matrix = np.array(fit["matrix"])
    before = matrix.copy()
    reference = {"image_points": project(FORWARD, PITCH_POINTS[[14, 15]]).tolist(),
                 "pitch_points": PITCH_POINTS[[14, 15]].tolist()}
    checked = check_landmarks(matrix, reference, 1)
    assert checked["status"] == "failed"
    assert checked["max_error_m"] > 1
    np.testing.assert_array_equal(matrix, before)  # Evaluation cannot refit.


def test_projection_rejects_horizon_and_shape_mismatch():
    with pytest.raises(ValueError):
        project(np.zeros((3, 3)), [[1, 1]])
    with pytest.raises(ValueError, match="sports32"):
        fit_pitch(np.ones((31, 2)), np.ones(31), (1920, 1080))


def test_leave_one_out_catches_residuals_before_returning_matrix():
    xy, confidence = observations()
    xy += np.random.default_rng(9).normal(0, 1, xy.shape)
    policy = FitPolicy(loo_median_px=0.01, loo_max_px=0.01)
    fit = fit_pitch(xy, confidence, (1920, 1080), policy)
    assert fit["reason"] == "leave_one_out_error"
    assert fit["matrix"] is None


def test_no_projective_horizon_inside_the_pitch():
    # Fit only the visible left side, but horizon would cross the unseen side.
    forward = np.array([[15., 0., 10.], [0., 8., 10.], [-0.015, 0., 1.]])
    xy = project(forward, PITCH_POINTS)
    confidence = np.zeros(32)
    confidence[:13] = 1
    fit = fit_pitch(xy, confidence, (1920, 1080))
    assert fit["reason"] == "pitch_horizon_crossing"
    assert fit["matrix"] is None


def test_runner_refuses_existing_outputs_and_unverified_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="new output"):
        inputs(tmp_path / "video.mp4", tmp_path / "model.pt", tmp_path / "checks.json", tmp_path)
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"not vendor checkpoint")
    with pytest.raises(ValueError, match="vendor-linked"):
        inputs(tmp_path / "video.mp4", weights, tmp_path / "checks.json", tmp_path / "new")
    monkeypatch.setattr(evaluator, "WEIGHTS_SHA256", hashlib.sha256(weights.read_bytes()).hexdigest())
    source, checks = tmp_path / "video.mp4", tmp_path / "checks.json"
    source.write_bytes(b"different video")
    checks.write_text(json.dumps({"source_sha256": "not-this-source"}))
    with pytest.raises(ValueError, match="different video"):
        inputs(source, weights, checks, tmp_path / "new")
