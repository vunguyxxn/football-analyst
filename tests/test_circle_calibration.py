import cv2
import numpy as np
import pytest
from backend.cv.circle_calibration import circle_matrix


def test_recovers_synthetic_camera_using_circle_and_touchlines():
    forward = np.array([[15., 3., 100], [.5, -8., 800], [.002, .008, 1.]])
    def project(points):
        return cv2.perspectiveTransform(np.float64([points]), forward)[0]
    theta = np.linspace(0, 2 * np.pi, 200)
    circle = np.c_[52.5 + 9.15 * np.cos(theta), 34 + 9.15 * np.sin(theta)]
    ellipse = cv2.fitEllipse(project(circle).astype(np.float32))
    inverse, quality = circle_matrix(ellipse, project([[52.5, 0]])[0], project([[52.5, 68]])[0])
    control = np.array([[10., 10.], [80., 30.], [20., 60.]])
    recovered = cv2.perspectiveTransform(project(control)[None], inverse)[0]
    assert np.max(np.abs(recovered - control)) < .002
    assert quality["diameter_error_px"] < .01


def test_rejects_touchlines_inconsistent_with_known_diameter_ratio():
    with pytest.raises(ValueError):
        circle_matrix(((400, 300), (500, 100), 0), [400, 360], [400, 240])
