import cv2
import numpy as np

from backend.cv.job_pitch_analysis import projection_quality, validation_pitch_pixels
from backend.cv.partial_pitch_calibration import fit_partial_pitch
from backend.cv.pitch_keypoints import PITCH_POINTS, project
from backend.cv.team_palette import TeamPalette


def penalty_view(curve=True):
    frame = np.full((720, 400, 3), (30, 140, 30), np.uint8)
    forward = np.array([[10., 0, 10], [0, -10., 700], [0, 0, 1.]])
    def line(a, b):
        points = project(forward, [a, b]).astype(int)
        cv2.line(frame, tuple(points[0]), tuple(points[1]), (245, 245, 245), 3)
    for y in (0, 68):
        line([0, y], [105, y])
    line([0, 0], [0, 68])
    for x, low, high in ((16.5, 13.84, 54.16), (5.5, 24.84, 43.16)):
        line([x, low], [x, high])
        line([0, low], [x, low])
        line([0, high], [x, high])
    if curve:
        theta = np.linspace(0, 2*np.pi, 720)
        world = np.c_[11+9.15*np.cos(theta), 34+9.15*np.sin(theta)]
        points = project(forward, world[world[:, 0] >= 16.5]).astype(np.int32)
        cv2.polylines(frame, [points], False, (245, 245, 245), 3)
    xy = project(forward, PITCH_POINTS)
    confidence = ((xy[:, 0] >= 4) & (xy[:, 0] < 396) & (xy[:, 1] >= 4) & (xy[:, 1] < 716)).astype(float)
    return frame, xy, confidence, np.linalg.inv(forward)


def test_partial_penalty_view_does_not_require_midfield_circle():
    frame, xy, confidence, expected = penalty_view()
    fit = fit_partial_pitch(frame, xy, confidence, quality=projection_quality, pixels=validation_pitch_pixels(frame))
    assert fit["status"] == "candidate", fit
    measured = project(np.array(fit["matrix"]), [[100, 200], [200, 500], [300, 400]])
    np.testing.assert_allclose(measured, project(expected, [[100, 200], [200, 500], [300, 400]]), atol=.6)
    assert fit["validation"] == "disjoint_curve_and_all_visible_markings"


def test_partial_lines_alone_cannot_validate_themselves():
    frame, xy, confidence, _ = penalty_view(curve=False)
    fit = fit_partial_pitch(frame, xy, confidence, quality=projection_quality, pixels=validation_pitch_pixels(frame))
    assert fit["status"] == "rejected"
    frame[:] = (30, 140, 30)
    assert fit_partial_pitch(frame, xy, confidence, quality=projection_quality)["status"] == "rejected"


def test_partial_fit_still_obeys_full_marking_gate():
    frame, xy, confidence, _ = penalty_view()
    fit = fit_partial_pitch(frame, xy, confidence, quality=lambda *_: {"passed": False}, pixels=validation_pitch_pixels(frame))
    assert fit["status"] == "rejected"


def test_palette_rejects_foreign_colour_without_inventing_role():
    rng = np.random.default_rng(44)
    features = np.r_[rng.normal([80, 121, 138], [6, 1, 1], (50, 3)),
                     rng.normal([235, 125, 132], [6, 1, 1], (50, 3)),
                     [[205, 114, 123], [210, 115, 124]]]
    palette = TeamPalette().fit(features)
    assert palette.predict_feature([80, 121, 138]) == "A"
    assert palette.predict_feature([235, 125, 132]) == "B"
    assert palette.predict_feature([210, 114, 123]) == "unknown"
    assert palette.predict_feature([244, 105, 154]) == "unknown"
    assert palette.predict_feature([np.nan, 100, 100]) == "unknown"
    assert palette.report()["semantic_referee_or_goalkeeper_verified"] is False
    assert palette.predict_feature(None) == "unknown"
    palette.fit([])
    assert palette.predict_feature([235, 125, 132]) == "unknown"


def test_green_cast_paint_needs_two_local_contrasts():
    from backend.cv.pitch_paint import paint_pixels
    hsv = np.full((180, 320, 3), (43, 185, 170), np.uint8)
    hsv[80:83, 30:290] = (43, 155, 200)
    hsv[120:123, 30:290] = (43, 185, 210)  # Bright only, not paint.
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    points = paint_pixels(frame, expanded=True).astype(int)
    assert len(points) > 700
    assert np.all((points[:, 1] >= 80) & (points[:, 1] < 83))
    assert len(validation_pitch_pixels(frame)) == 0  # Search evidence cannot loosen publication.


def test_square_fallback_maps_image_pixels_back_before_fitting(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import ultralytics
    from backend.cv import job_pitch_analysis as module
    weights = tmp_path / "pose.pt"
    weights.write_bytes(b"local checkpoint stub")
    monkeypatch.setattr(module, "WEIGHTS", weights)
    monkeypatch.setattr(module, "WEIGHTS_HASH", module.digest(weights))
    def tensor(array):
        return SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: array.copy()))
    xy = np.full((32, 2), 160.)
    prediction = SimpleNamespace(boxes=[1], keypoints=SimpleNamespace(xy=[tensor(xy)], conf=[tensor(np.ones(32))]))
    shapes, fitted = [], []
    def predict(frame, **kwargs):
        shapes.append(frame.shape[:2])
        return [prediction]
    model = SimpleNamespace(task="pose", model=SimpleNamespace(yaml={"kpt_shape": [32, 3]}), predict=predict)
    monkeypatch.setattr(ultralytics, "YOLO", lambda _: model)
    def matrix(frame, points, confidence):
        fitted.append(points.copy())
        return np.eye(3) if len(fitted) == 2 else None
    monkeypatch.setattr(module, "automatic_matrix", matrix)
    find = module.automatic_finder()
    np.testing.assert_equal(find(np.zeros((720, 1280, 3), np.uint8)), np.eye(3))
    assert shapes == [(720, 1280), (640, 640)]
    np.testing.assert_allclose(fitted[1], np.tile([320, 180], (32, 1)))


def test_palette_sampling_recovers_when_initial_probes_have_no_boundary(monkeypatch):
    from types import SimpleNamespace
    from backend.cv import pitch_boundary, team_classifier
    from backend.cv.upload_analysis import learn_palette
    initial = set(np.linspace(0, 179, 12, dtype=int))
    class Capture:
        frame = 0
        def set(self, _, frame):
            self.frame = int(frame)
        def read(self):
            return True, np.full((30, 60, 3), self.frame, np.uint8)
        def release(self):
            pass
    monkeypatch.setattr(cv2, "VideoCapture", lambda _: Capture())
    monkeypatch.setattr(pitch_boundary, "pitch_region", lambda image: None if int(image[0, 0, 0]) in initial else np.ones((4, 2)))
    monkeypatch.setattr(pitch_boundary, "inside_pitch", lambda region, box: region is not None)
    monkeypatch.setattr(team_classifier, "jersey_feature", lambda image, box, mode: np.array([80, 121, 138]) if box[0] < 10 else np.array([235, 125, 132]))
    boxes = np.array([[0, 0, 8, 25]]*10+[[20, 0, 30, 25]]*10)
    prediction = SimpleNamespace(boxes=SimpleNamespace(xyxy=SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: boxes))))
    model = SimpleNamespace(predict=lambda *args, **kwargs: [prediction])
    palette, report = learn_palette("source", {"frames": 180}, model, [0], 640, "cpu", lambda **_: None, lambda: False)
    assert palette.centers is not None
    assert report["extra_probes"] > 0 and len(report["feature_frames"]) >= 2
    assert report["features"] <= 300
    assert palette.predict_feature([80, 121, 138]) == "A"


def test_straight_lines_cannot_compensate_for_weak_circle_witness():
    frame = np.full((680, 1050, 3), (30, 140, 30), np.uint8)
    for x in (165, 525, 885):
        cv2.line(frame, (x, 138), (x, 542), (245, 245, 245), 3)
    cv2.line(frame, (525, 0), (525, 679), (245, 245, 245), 3)
    for x1, x2 in ((0, 165), (885, 1049)):
        for y in (138, 542):
            cv2.line(frame, (x1, y), (x2, y), (245, 245, 245), 3)
    cv2.ellipse(frame, (525, 340), (92, 92), 0, 0, 240, (245, 245, 245), 3)
    matrix = np.array([[.1, 0, 0], [0, -.1, 68], [0, 0, 1.]])
    checked = projection_quality(frame, matrix)
    assert all(r["passed"] for r in checked["markings"] if r["family"] != "curve")
    assert not checked["passed"]
    cv2.circle(frame, (525, 340), 92, (245, 245, 245), 3)
    assert projection_quality(frame, matrix)["passed"]
