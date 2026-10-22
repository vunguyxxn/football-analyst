import cv2
import numpy as np
import pytest

from backend.cv.camera_motion import CameraMotion


def scene():
    rng = np.random.default_rng(43)
    image = np.zeros((360, 640, 3), dtype=np.uint8)
    image[:, :, 1] = rng.integers(75, 200, (360, 640), dtype=np.uint8)
    return cv2.GaussianBlur(image, (3, 3), 0)


def anchor():
    return np.array([[105/640, 0, 0], [0, -68/360, 68], [0, 0, 1.]])


@pytest.mark.parametrize("scale", [1., 1.015])
def test_pan_zoom_keep_stationary_ground_point_fixed(scale):
    first = scene()
    motion = CameraMotion()
    reference = anchor()
    assert motion.update(first, [], reference)["status"] == "manual_anchor"
    warp = np.array([[scale, .001, 4], [-.001, scale, 2], [0, 0, 1.]])
    second = cv2.warpPerspective(first, warp, (640, 360))
    result = motion.update(second, [])
    assert result["status"] == "tracked"
    point = np.array([300., 170., 1.])
    projected = motion.matrix @ warp @ point
    expected = reference @ point
    assert projected[:2]/projected[2] == pytest.approx(expected[:2], abs=.08)


def test_failure_latches_until_explicit_manual_anchor():
    motion = CameraMotion()
    image = scene()
    motion.update(image, [], anchor())
    assert motion.update(np.zeros_like(image), [])["status"] == "lost"
    assert motion.matrix is None
    assert motion.update(image, [])["status"] == "lost"
    assert motion.update(image, [], anchor())["status"] == "manual_anchor"
    assert motion.update(image, [])["status"] == "tracked"


def test_people_and_off_pitch_regions_are_excluded():
    image = scene()
    mask = CameraMotion.ground_mask(image, anchor(), [[100, 100, 150, 180]])
    assert not mask[90:190, 90:160].any()
    assert mask[200:250, 300:350].any()
    off_pitch = anchor()
    off_pitch[0, 2] = 106
    assert not CameraMotion.ground_mask(image, off_pitch, []).any()


def test_unchecked_chain_expires():
    image = scene()
    motion = CameraMotion()
    motion.update(image, [], anchor())
    motion.age = 300
    result = motion.update(image, [])
    assert result["status"] == "lost"
    assert result["reason"] == "reanchor_interval_exceeded"


def test_projection_stops_after_camera_loss_and_reanchors(tmp_path):
    import hashlib
    import json
    from backend.cv.homography import PitchCalibration
    source = tmp_path / "video.mp4"
    source.write_bytes(b"identity")
    segment = {"start_frame": 0, "end_frame": 3,
               "image_points": [[0, 359], [639, 359], [639, 0], [0, 0]],
               "pitch_points": [[0, 0], [105, 0], [105, 68], [0, 68]]}
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                "image_size": [640, 360], "segments": [segment, {**segment, "start_frame": 3, "end_frame": 5}]}))
    calibration = PitchCalibration(source, path, 640, 360, True)
    image = scene()
    assert calibration.project(0, 30, 1, "A", [290, 100, 310, 170]) is None
    calibration.prepare(0, image, [])
    assert calibration.project(0, 30, 1, "A", [290, 100, 310, 170]) is not None
    calibration.prepare(1, np.zeros_like(image), [])
    assert calibration.project(1, 30, 1, "A", [290, 100, 310, 170]) is None
    calibration.prepare(2, image, [])
    assert calibration.project(2, 30, 1, "A", [290, 100, 310, 170]) is None
    calibration.prepare(3, image, [])
    assert calibration.project(3, 30, 1, "A", [290, 100, 310, 170])[0] == 1
