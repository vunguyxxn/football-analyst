import cv2
import numpy as np
import pytest

from backend.cv.pitch_keypoints import PITCH_POINTS, project
from backend.cv.pitch_line_calibration import LinePolicy, check_circle, check_penalty_sides, fit_four_lines, fit_line_pitch


FORWARD = np.array([[10., 1., 100.], [.2, -8., 800.], [.001, .0005, 1.]])


def image_lines(forward, x=88.5):
    return [np.linalg.inv(forward).T @ line for line in
            ([1., 0., -52.5], [1., 0., -x], [0., 1., -68.], [0., 1., 0.])]


@pytest.mark.parametrize("penalty_x", [16.5, 88.5])
def test_four_observed_lines_recover_metric_without_circle_fit(penalty_x):
    lines = image_lines(FORWARD, penalty_x)
    matrix = fit_four_lines(*lines, penalty_x)
    np.testing.assert_allclose(project(matrix, project(FORWARD, PITCH_POINTS)), PITCH_POINTS, atol=1e-4)


def test_parallel_degenerate_and_mirrored_geometry_is_rejected():
    lines = image_lines(FORWARD)
    with pytest.raises(ValueError, match="intersection"):
        fit_four_lines(lines[0], lines[1], lines[0], lines[3], 88.5)
    flipped = np.array([[-1., 0., 1280.], [0., 1., 0.], [0., 0., 1.]]) @ FORWARD
    with pytest.raises(ValueError, match="mirrored"):
        fit_four_lines(*image_lines(flipped), 88.5)


def test_lines_used_to_fit_are_excluded_from_circle_validation():
    policy = LinePolicy()
    pixels = []
    for a, b in [([0, 68], [105, 68]), ([0, 0], [105, 0]), ([52.5, 0], [52.5, 68]),
                 ([88.5, 13.84], [88.5, 54.16]), ([88.5, 54.16], [105, 54.16]),
                 ([88.5, 13.84], [105, 13.84])]:
        pixels.extend(project(FORWARD, np.linspace(a, b, 500)))
    lines = image_lines(FORWARD)
    lines = np.array([line / np.linalg.norm(line[:2]) for line in lines])
    checked = check_circle(np.linalg.inv(FORWARD), np.array(pixels), (1280, 900), lines, policy)
    assert checked["status"] == "failed"
    # Add held-out circle support, without changing the matrix or fit lines.
    theta = np.linspace(0, 2 * np.pi, 1000)
    pixels.extend(project(FORWARD, np.c_[52.5 + 9.15 * np.cos(theta), 34 + 9.15 * np.sin(theta)]))
    matrix = np.linalg.inv(FORWARD)
    before = matrix.copy()
    assert check_circle(matrix, np.array(pixels), (1280, 900), lines, policy)["status"] == "passed"
    np.testing.assert_array_equal(matrix, before)


def test_line_pipeline_corrects_model_seeds_and_rejects_absent_evidence():
    forward = np.array([[10., 0., 100.], [0., -10., 800.], [0., 0., 1.]])
    frame = np.full((900, 1280, 3), (40, 130, 40), dtype=np.uint8)
    xy = project(forward, PITCH_POINTS) + [12, -8]
    assert fit_line_pitch(frame, xy, np.ones(32))["matrix"] is None
    cv2.ellipse(frame, ((625., 460.), (183., 183.), 0.), (245, 245, 245), 3)
    for a, b in [([0, 68], [105, 68]), ([0, 0], [105, 0]), ([52.5, 0], [52.5, 68]),
                 ([88.5, 13.84], [88.5, 54.16]), ([88.5, 54.16], [105, 54.16]),
                 ([88.5, 13.84], [105, 13.84])]:
        p = np.rint(project(forward, [a, b])).astype(int)
        cv2.line(frame, tuple(p[0]), tuple(p[1]), (245, 245, 245), 3)
    result = fit_line_pitch(frame, xy, np.ones(32))
    assert result["status"] == "candidate", result
    assert result["circle_check"]["status"] == "passed"
    assert result["penalty_x_m"] == 88.5
    checked = project(np.array(result["matrix"]), project(forward, [[30, 20], [88.5, 50], [100, 10]]))
    np.testing.assert_allclose(checked, [[30, 20], [88.5, 50], [100, 10]], atol=.3)
    frame[795:806] = (40, 130, 40)  # Remove near touchline; it cannot be invented.
    assert fit_line_pitch(frame, xy, np.ones(32))["matrix"] is None


def test_penalty_sides_detect_wrong_width_without_refitting_matrix():
    pixels = []
    for y in (13.84, 54.16):
        pixels.extend(project(FORWARD, np.c_[np.linspace(88.5, 105, 500), np.full(500, y)]))
    pixels = np.rint(pixels).astype(np.float32)
    correct = np.linalg.inv(FORWARD)
    assert check_penalty_sides(correct, pixels, (1280, 900), 88.5)["status"] == "passed"
    wrong = np.array([[1, 0, 0], [0, 1, 3], [0, 0, 1.]]) @ correct
    before = wrong.copy()
    assert check_penalty_sides(wrong, pixels, (1280, 900), 88.5)["status"] == "failed"
    np.testing.assert_array_equal(wrong, before)


def test_both_valid_penalty_sides_are_reported_as_ambiguous():
    forward = np.array([[10., 0., 100.], [0., -10., 800.], [0., 0., 1.]])
    frame = np.full((900, 1280, 3), (40, 130, 40), dtype=np.uint8)
    cv2.ellipse(frame, ((625., 460.), (183., 183.), 0.), (245, 245, 245), 3)
    segments = [([0, 68], [105, 68]), ([0, 0], [105, 0]), ([52.5, 0], [52.5, 68])]
    for x, goal in ((16.5, 0), (88.5, 105)):
        segments.extend([([x, 13.84], [x, 54.16]), ([x, 13.84], [goal, 13.84]), ([x, 54.16], [goal, 54.16])])
    for a, b in segments:
        p = np.rint(project(forward, [a, b])).astype(int)
        cv2.line(frame, tuple(p[0]), tuple(p[1]), (245, 245, 245), 3)
    result = fit_line_pitch(frame, project(forward, PITCH_POINTS) + [12, -8], np.ones(32))
    assert result["reason"] == "ambiguous_four_line_solutions"
    assert result["matrix"] is None
