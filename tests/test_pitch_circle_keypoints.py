import cv2
import numpy as np
import pytest

from backend.cv.pitch_circle_keypoints import CirclePolicy, check_penalty_lines, fit_circle_pitch, matrix_from_one_edge
from backend.cv.pitch_keypoints import PITCH_POINTS, project


FORWARD = np.array([[10., 1., 100.], [0.2, -8., 800.], [0.001, 0.0005, 1.]])


def circle_observations():
    angles = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    circle = np.c_[52.5 + 9.15 * np.cos(angles), 34 + 9.15 * np.sin(angles)]
    pixels = project(FORWARD, circle)
    ellipse = cv2.fitEllipse(pixels.astype(np.float32))
    ends = project(FORWARD, [[52.5, 68], [52.5, 0]])
    line = np.cross(np.r_[ends[0], 1.], np.r_[ends[1], 1.])
    line /= np.linalg.norm(line[:2])
    return ellipse, line, ends, pixels


@pytest.mark.parametrize("edge_y,edge_index", [(68, 0), (0, 1)])
def test_circle_and_one_observed_touchline_recover_full_projective_metric(edge_y, edge_index):
    ellipse, line, ends, _ = circle_observations()
    matrix = matrix_from_one_edge(ellipse, line, ends[edge_index], edge_y)
    # Includes off-diameter points: ellipse extrema are not cardinal controls.
    np.testing.assert_allclose(project(matrix, project(FORWARD, PITCH_POINTS)), PITCH_POINTS, atol=2e-4)


def test_wrong_touchline_side_and_line_missing_circle_are_rejected():
    ellipse, line, ends, _ = circle_observations()
    with pytest.raises(ValueError, match="outside_circle"):
        matrix_from_one_edge(ellipse, line, ends[0], 0)
    faraway_line = np.array([0., 1., -1000.])
    with pytest.raises(ValueError, match="cross_circle"):
        matrix_from_one_edge(ellipse, faraway_line, [500., 1000.], 68)


def test_no_white_support_or_uncertain_seeds_never_produce_calibration():
    frame = np.full((900, 1280, 3), (40, 130, 40), dtype=np.uint8)
    xy = project(FORWARD, PITCH_POINTS)
    assert fit_circle_pitch(frame, xy, np.zeros(32))["matrix"] is None
    result = fit_circle_pitch(frame, xy, np.ones(32))
    assert result["status"] == "rejected"
    assert result["matrix"] is None


def test_white_geometry_corrects_displaced_model_prior_without_manual_anchors():
    frame = np.full((900, 1280, 3), (40, 130, 40), dtype=np.uint8)
    # Symmetric rasterization keeps this positive image test well conditioned;
    # projective/off-diameter recovery is separately tested analytically above.
    forward = np.array([[10., 0., 100.], [0., -10., 800.], [0., 0., 1.]])
    cv2.ellipse(frame, ((625., 460.), (183., 183.), 0.), (245, 245, 245), 3)
    for a, b in [([0, 68], [105, 68]), ([0, 0], [105, 0]), ([52.5, 0], [52.5, 68]),
                 ([16.5, 13.84], [16.5, 54.16]), ([88.5, 13.84], [88.5, 54.16])]:
        points = np.rint(project(forward, [a, b])).astype(int)
        cv2.line(frame, tuple(points[0]), tuple(points[1]), (245, 245, 245), 3)
    xy = project(forward, PITCH_POINTS) + [12., -8.]
    confidence = np.ones(32)
    xy[30], confidence[30] = [np.nan, np.nan], np.nan
    result = fit_circle_pitch(frame, xy, confidence)
    assert result["status"] == "candidate", result
    assert result["circle_inlier_pixels"] >= 300
    matrix = np.array(result["matrix"])
    checked = project(matrix, project(forward, [[40, 20], [60, 50], [52.5, 34]]))
    np.testing.assert_allclose(checked, [[40, 20], [60, 50], [52.5, 34]], atol=.3)


def test_disjoint_line_check_rejects_coherent_but_wrong_circle_metric_without_refit():
    pixels = []
    for x in (16.5, 88.5):
        pixels.extend(project(FORWARD, np.c_[np.full(300, x), np.linspace(13.84, 54.16, 300)]))
    pixels = np.rint(pixels).astype(np.float32)
    correct = np.linalg.inv(FORWARD)
    policy = CirclePolicy()
    assert check_penalty_lines(correct, pixels, (1280, 900), policy)["status"] == "passed"
    wrong = np.array([[1, 0, 3], [0, 1, 0], [0, 0, 1.]]) @ correct
    before = wrong.copy()
    assert check_penalty_lines(wrong, pixels, (1280, 900), policy)["status"] == "failed"
    np.testing.assert_array_equal(wrong, before)


def test_low_pixel_circle_residual_does_not_override_bad_far_field_geometry():
    frame = np.full((900, 1280, 3), (40, 130, 40), dtype=np.uint8)
    circle = circle_observations()[3]
    # Integer truncation shifts the conic by a fraction of a pixel. A circle
    # fit can look excellent while the extrapolated far-field scale is wrong.
    cv2.polylines(frame, [circle.astype(np.int32)], True, (245, 245, 245), 3)
    for a, b in [([0, 68], [105, 68]), ([0, 0], [105, 0]), ([52.5, 0], [52.5, 68]),
                 ([16.5, 13.84], [16.5, 54.16]), ([88.5, 13.84], [88.5, 54.16])]:
        points = project(FORWARD, [a, b]).astype(int)
        cv2.line(frame, tuple(points[0]), tuple(points[1]), (245, 245, 245), 3)
    result = fit_circle_pitch(frame, project(FORWARD, PITCH_POINTS) + [12, -8], np.ones(32))
    assert result["circle_median_residual_px"] < 2
    assert result["reason"] == "penalty_line_unsupported"
    assert result["matrix"] is None
