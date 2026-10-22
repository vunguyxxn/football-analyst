import hashlib
import json

import numpy as np
import pytest

from backend.cv.landmark_guard import LandmarkGuard


def config(tmp_path):
    payload = {"source_sha256": "identity", "image_size": [105, 68],
               "max_error_m": 1.0, "max_gap_frames": 3,
               "checkpoints": [{"frame": 1, "image_points": [[20, 20], [40, 40]],
                                "pitch_points": [[20, 20], [40, 40]]},
                               {"frame": 11, "image_points": [[20, 20], [40, 40]],
                                "pitch_points": [[20, 20], [40, 40]]}]}
    path = tmp_path / "checks.json"
    path.write_text(json.dumps(payload))
    return path, payload


def load(path):
    return LandmarkGuard(path, "identity", 105, 68, [(0, 10), (10, 20)])


def test_pending_verified_expired_and_reanchor(tmp_path):
    path, _ = config(tmp_path)
    guard = load(path)
    assert guard.check(0, np.eye(3))["status"] == "pending"
    assert guard.check(1, np.eye(3))["status"] == "verified"
    assert guard.check(4, np.eye(3))["status"] == "verified"
    assert guard.check(5, np.eye(3))["reason"] == "landmark_check_expired"
    assert guard.check(11, np.eye(3))["status"] == "lost"
    guard.start_segment(10)
    assert guard.check(10, np.eye(3))["status"] == "pending"
    assert guard.check(11, np.eye(3))["status"] == "verified"


def test_drift_is_not_clamped_or_used_to_refit(tmp_path):
    path, _ = config(tmp_path)
    guard = load(path)
    matrix = np.eye(3)
    matrix[0, 2] = 1.1
    original = matrix.copy()
    result = guard.check(1, matrix)
    assert result["reason"] == "landmark_drift_exceeded"
    assert result["max_error_m"] == pytest.approx(1.1)
    assert np.array_equal(original, matrix)
    assert guard.check(2, np.eye(3))["status"] == "lost"


@pytest.mark.parametrize("option", [
    {"source_sha256": "wrong"}, {"image_size": [10, 10]},
    {"max_error_m": float("nan")}, {"max_error_m": 0}, {"max_gap_frames": 0},
    {"max_gap_frames": 1.5}, {"checkpoints": []},
])
def test_invalid_config_rejected(tmp_path, option):
    path, payload = config(tmp_path)
    payload.update(option)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load(path)


@pytest.mark.parametrize("option", [
    {"frame": 0}, {"frame": 20}, {"frame": True},
    {"image_points": [[20,20]]}, {"pitch_points": [[20,20]]},
    {"image_points": [[20,20],[105,40]]},
    {"pitch_points": [[20,20],[106,40]]},
    {"image_points": [[20,20],[20,20]]},
    {"pitch_points": [[20,20],[float('inf'),40]]},
])
def test_invalid_checkpoints_rejected(tmp_path, option):
    path, payload = config(tmp_path)
    payload["checkpoints"][0].update(option)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load(path)


def test_first_check_cannot_arrive_after_expiry(tmp_path):
    path, payload = config(tmp_path)
    payload["checkpoints"][0]["frame"] = 5
    path.write_text(json.dumps(payload))
    result = load(path).check(5, np.eye(3))
    assert result["reason"] == "landmark_check_expired"


def test_guard_blocks_projection_even_when_camera_reports_tracked(tmp_path, monkeypatch):
    from backend.cv.homography import PitchCalibration
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(json.dumps({"source_sha256": digest, "image_size": [105, 68],
        "segments": [{"start_frame": 0, "end_frame": 10,
                      "image_points": [[0, 0], [104, 0], [104, 67], [0, 67]],
                      "pitch_points": [[0, 0], [104, 0], [104, 67], [0, 67]]}]}))
    path, payload = config(tmp_path)
    payload["source_sha256"] = digest
    payload["checkpoints"] = payload["checkpoints"][:1]
    payload["checkpoints"][0]["pitch_points"] = [[25, 20], [45, 40]]
    path.write_text(json.dumps(payload))
    calibration = PitchCalibration(source, calibration_path, 105, 68, True, path)
    def successful_camera(*args, **kwargs):
        calibration.motion.matrix = np.eye(3)
        return {"status": "tracked"}
    monkeypatch.setattr(calibration.motion, "update", successful_camera)
    assert calibration.prepare(0, None, [])["status"] == "awaiting_landmark_check"
    assert calibration.project(0, 60, 1, "A", [20, 10, 40, 30]) is None
    assert calibration.prepare(1, None, [])["reason"] == "landmark_drift_exceeded"
    assert calibration.project(1, 60, 1, "A", [20, 10, 40, 30]) is None
    assert calibration.motion.failed


def test_guard_allows_valid_projection_then_expires(tmp_path, monkeypatch):
    from backend.cv.homography import PitchCalibration
    source=tmp_path/'video'; source.write_bytes(b'video')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    calibration_path=tmp_path/'calibration.json'
    calibration_path.write_text(json.dumps({'source_sha256':digest,'image_size':[105,68],
        'segments':[{'start_frame':0,'end_frame':10,'image_points':[[0,0],[104,0],[104,67],[0,67]],
                     'pitch_points':[[0,0],[104,0],[104,67],[0,67]]}]}))
    path,payload=config(tmp_path)
    payload['source_sha256']=digest;payload['checkpoints']=payload['checkpoints'][:1]
    path.write_text(json.dumps(payload))
    calibration=PitchCalibration(source,calibration_path,105,68,True,path)
    def success(*args, **kwargs):
        calibration.motion.matrix=np.eye(3)
        return {'status':'tracked'}
    monkeypatch.setattr(calibration.motion,'update',success)
    calibration.prepare(0,None,[])
    assert calibration.prepare(1,None,[])['status']=='tracked'
    assert calibration.project(1,60,1,'A',[20,10,40,30]) is not None
    assert calibration.prepare(5,None,[])['reason']=='landmark_check_expired'
    assert calibration.project(5,60,1,'A',[20,10,40,30]) is None
