import hashlib
import json

import numpy as np
import pytest

from backend.common.schemas import TrackingRow
from backend.cv.homography import PitchCalibration, matrix_for
from backend.cv.pitch_metrics import PitchMetrics


def calibration_file(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video identity")
    path = tmp_path / "calibration.json"
    payload = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "image_size": [1200, 800], "segments": [
                   {"start_frame": 0, "end_frame": 30,
                    "image_points": [[100, 700], [1150, 700], [1150, 20], [100, 20]],
                    "pitch_points": [[0, 0], [105, 0], [105, 68], [0, 68]]}]}
    path.write_text(json.dumps(payload))
    return source, path, payload


def test_project_footpoint_in_metres_and_frame_scope(tmp_path):
    source, path, _ = calibration_file(tmp_path)
    calibration = PitchCalibration(source, path, 1200, 800)
    segment, row = calibration.project(15, 30, 7, "A", [615, 200, 635, 360])
    assert segment == 0
    assert row.x_m == pytest.approx(52.5)
    assert row.y_m == pytest.approx(34)
    assert row.time_s == .5
    assert row.team == "A"
    assert calibration.project(30, 30, 7, "A", [615, 200, 635, 360]) is None
    assert calibration.project(0, 30, 7, "A", [0, 200, 20, 360]) is None


@pytest.mark.parametrize("points", [
    [[0, 0]]*4, [[0, 0], [1, 0], [2, 0], [0, 1]],
    [[0, 0], [1, 0], [1, 1], [float('nan'), 1]], [[0, 0], [1, 1]],
])
def test_degenerate_points_rejected(points):
    with pytest.raises(ValueError):
        matrix_for(points, [[0, 0], [105, 0], [105, 68], [0, 68]])


def test_perspective_projection_of_independent_interior_point():
    # Generate camera quadrilateral from a known non-affine projective map.
    world = np.array([[0, 0], [105, 0], [105, 68], [0, 68]], dtype=float)
    camera = np.array([[5, .2, 100], [.1, -4, 600], [.002, .001, 1.]])
    def to_pixel(points):
        homogeneous = np.c_[points, np.ones(len(points))] @ camera.T
        return homogeneous[:, :2] / homogeneous[:, 2:]
    inverse = matrix_for(to_pixel(world), world)
    pixel = to_pixel([[30, 40]])[0]
    result = inverse @ [*pixel, 1]
    assert result[:2]/result[2] == pytest.approx([30, 40], abs=1e-4)


def test_wrong_source_dimensions_and_overlap_rejected(tmp_path):
    source, path, payload = calibration_file(tmp_path)
    with pytest.raises(ValueError, match="mismatch"):
        PitchCalibration(source, path, 100, 100)
    payload["segments"].append(payload["segments"][0])
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="disjoint"):
        PitchCalibration(source, path, 1200, 800)
    source.write_bytes(b"replacement")
    with pytest.raises(ValueError, match="mismatch"):
        PitchCalibration(source, path, 1200, 800)


def row(time, x, track=1, y=34):
    return TrackingRow(frame=round(time*60), time_s=time, track_id=track, team="A", x_m=x, y_m=y)


def test_known_distance_speed_heatmap_and_breaks():
    metrics = PitchMetrics(60)
    # 2 m/s = 7.2 km/h, including many 60 FPS observations.
    for frame in range(61):
        metrics.observe(0, row(frame/60, 10 + 2*frame/60))
    report = metrics.report()
    track = report["tracks"][0]
    assert track["distance_m"] == pytest.approx(2)
    assert track["duration_s"] == pytest.approx(1)
    assert track["max_speed_kmh"] == pytest.approx(7.2)
    assert sum(map(sum, track["heatmap"])) == 61
    # Reject teleport, reset anchor; a gap and calibration boundary add no distance.
    metrics.observe(0, row(1.5, 90))
    metrics.observe(0, row(2, 90))
    metrics.observe(0, row(4, 95))
    metrics.observe(1, row(4.5, 0))
    metrics.observe(0, row(4.5, 95, track=2))
    tracks = metrics.report()["tracks"]
    assert tracks[0]["distance_m"] == pytest.approx(2)
    assert tracks[0]["rejected_steps"] == 1
    assert all(track["distance_m"] == 0 for track in tracks[1:])


def test_heatmap_axes_and_boundary():
    metrics = PitchMetrics(60)
    metrics.observe(0, row(0, 0, y=0))
    metrics.observe(0, row(0, 105, track=2, y=68))
    tracks = metrics.report()["tracks"]
    assert tracks[0]["heatmap"][0][0] == 1
    assert tracks[1]["heatmap"][13][20] == 1
