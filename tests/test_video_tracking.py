import sys
from types import SimpleNamespace

import pytest

from backend.cv.track_video import track_video


def test_missing_video_is_rejected_before_loading_cv(tmp_path):
    with pytest.raises(FileNotFoundError, match="Video not found"):
        track_video(tmp_path / "missing.mp4", tmp_path / "out.mp4", tmp_path / "m.pt")


@pytest.mark.parametrize("option", [
    {"chunk_seconds": 0}, {"chunk_seconds": float("nan")},
    {"confidence": 0}, {"confidence": float("nan")}, {"image_size": 31},
    {"landmark_checks": "checks.json"}, {"on_pitch_only": True}, {"smooth_pitch": True},
])
def test_invalid_options_are_rejected(tmp_path, option):
    source, weights = tmp_path / "in.mp4", tmp_path / "m.pt"
    source.touch()
    weights.touch()
    with pytest.raises(ValueError):
        track_video(source, tmp_path / "out.mp4", weights, **option)


def test_existing_output_is_not_overwritten(tmp_path):
    source, weights, output = [tmp_path / name for name in ("in.mp4", "m.pt", "out.mp4")]
    source.touch()
    weights.touch()
    output.write_bytes(b"keep")
    with pytest.raises(ValueError, match="new file"):
        track_video(source, output, weights)
    assert output.read_bytes() == b"keep"


@pytest.mark.parametrize("has_detection", [True, False])
@pytest.mark.parametrize("team_mode", [True, False])
@pytest.mark.parametrize("pitch_mode", [True, False, "moving", "guarded", "smoothed"])
def test_video_round_trip_preserves_ids_across_chunks(tmp_path, monkeypatch, has_detection, team_mode, pitch_mode):
    """Use real codec and ByteTrack with deterministic detector boxes."""
    cv2 = pytest.importorskip("cv2")
    sv = pytest.importorskip("supervision")
    np = pytest.importorskip("numpy")
    pytest.importorskip("torch")
    source, output, weights = [tmp_path / name for name in ("in.mp4", "out.mp4", "m.pt")]
    weights.touch()
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (96, 64))
    assert writer.isOpened()
    for _ in range(23):
        writer.write(np.zeros((64, 96, 3), dtype=np.uint8))
    writer.release()
    import hashlib
    import json
    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "image_size": [96, 64], "segments": [
            {"start_frame": 0, "end_frame": 23,
             "image_points": [[0, 63], [95, 63], [95, 0], [0, 0]],
             "pitch_points": [[0, 0], [105, 0], [105, 68], [0, 68]]}]}))
    observed_ids = []
    observed_detections = []
    real_update = sv.ByteTrack.update_with_detections

    def update(tracker, detections):
        result = real_update(tracker, detections)
        observed_ids.append(result.tracker_id.tolist())
        observed_detections.append(result)
        return result

    class Detector:
        names = {0: "person"}

        def __init__(self, path):
            pass

        def predict(self, frame, **kwargs):
            assert kwargs["classes"] == [0]
            pixels = np.array([[20, 10, 40, 50], [55, 10, 75, 50]], dtype=np.float32)
            return [SimpleNamespace(boxes=SimpleNamespace(xyxy=SimpleNamespace(
                cpu=lambda: SimpleNamespace(numpy=lambda: pixels)) ))]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=Detector))
    monkeypatch.setattr(sv.ByteTrack, "update_with_detections", update)
    monkeypatch.setattr(sv.Detections, "from_ultralytics", staticmethod(lambda _: (
        sv.Detections(
            xyxy=np.array([[20, 10, 40, 50], [55, 10, 75, 50]], dtype=np.float32),
            confidence=np.array([0.95, 0.95], dtype=np.float32), class_id=np.array([0, 0]),
        ) if has_detection else sv.Detections.empty()
    )))
    if team_mode:
        import itertools
        from backend.cv import team_classifier

        roles = itertools.cycle(["A", "B", "referee", "unknown"])
        monkeypatch.setattr(team_classifier, "fit_from_samples", lambda *_: SimpleNamespace(predict=lambda *_: next(roles)))
    check_path = None
    if pitch_mode == "guarded":
        from backend.cv.camera_motion import CameraMotion
        # Test pipeline gating with a deterministic static camera, real codec
        # and ByteTrack. Camera estimation itself is covered by other tests.
        def stable_camera(self, image, boxes, anchor=None):
            if anchor is not None:
                self.matrix = anchor.copy()
                self.failed = False
            return {"status": "tracked" if self.matrix is not None else "lost"}
        monkeypatch.setattr(CameraMotion, "update", stable_camera)
        check_path = tmp_path / "checks.json"
        check_path.write_text(json.dumps({"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "image_size": [96, 64], "max_gap_frames": 3, "max_error_m": .1,
            "checkpoints": [{"frame": 1, "image_points": [[30, 50], [65, 50]],
                             "pitch_points": [[30*105/95, 13*68/63], [65*105/95, 13*68/63]]}]}))
    summary = track_video(source, output, weights, device="cpu", chunk_seconds=0.5,
                          team_samples=tmp_path / "samples.json" if team_mode else None,
                          calibration=calibration if pitch_mode else None,
                          pitch_output=tmp_path / "pitch" if pitch_mode else None,
                          compensate_camera=pitch_mode in ("moving", "guarded"),
                          landmark_checks=check_path, smooth_pitch=pitch_mode == "smoothed")
    from backend.common.schemas import TrackingRow
    if pitch_mode:
        rows = [TrackingRow.model_validate_json(line) for line in
                (tmp_path / "pitch/tracking.jsonl").read_text().splitlines()]
        expected = {"moving": 2, "guarded": 8, "smoothed": 42}.get(pitch_mode, 46)
        assert len(rows) == expected*int(has_detection)
        assert summary["projected_rows"] == len(rows)
        assert all(0 <= row.x_m <= 105 and 0 <= row.y_m <= 68 for row in rows)
        report = json.loads((tmp_path / "pitch/metrics.json").read_text())
        assert len(report["tracks"]) == 2*int(has_detection)
        assert all(track["distance_m"] == pytest.approx(0, abs=1e-10)
                   for track in report["tracks"])
        if pitch_mode == "smoothed":
            raw = (tmp_path / "pitch/tracking_raw.jsonl").read_text().splitlines()
            quality = [json.loads(line) for line in (tmp_path / "pitch/smoothing_quality.jsonl").read_text().splitlines()]
            assert len(raw) == len(quality) == 46*int(has_detection)
            assert sum(q['status']=='warming_up' for q in quality) == 4*int(has_detection)
            assert report['pitch_smoothing'] is True
        if pitch_mode == "moving":
            quality = [json.loads(line) for line in (tmp_path / "pitch/camera_quality.jsonl").read_text().splitlines()]
            assert len(quality) == 23
            assert quality[0]["status"] == "manual_anchor"
            assert all(item["status"] == "lost" for item in quality[1:])
        if pitch_mode == "guarded":
            quality = [json.loads(line) for line in (tmp_path / "pitch/camera_quality.jsonl").read_text().splitlines()]
            assert quality[0]["status"] == "awaiting_landmark_check"
            assert all(item["status"] == "tracked" for item in quality[1:5])
            assert quality[5]["reason"] == "landmark_check_expired"
            assert all(item["status"] == "lost" for item in quality[5:])
            assert all(1 <= row.frame <= 4 for row in rows)
            assert report["landmark_checks"]["max_gap_frames"] == 3
    else:
        assert "pitch_output" not in summary
        assert not (tmp_path / "pitch").exists()
    if team_mode:
        assert summary["team_observations"] == (
            {"A": 0, "B": 0, "referee": 0, "unknown": 46} if has_detection
            else {"A": 0, "B": 0, "referee": 0, "unknown": 0}
        )
    assert summary["frames"] == 23
    assert summary["chunks"] == 5
    assert len(observed_ids) == 23
    assert all(np.all(detections.class_id == 0) for detections in observed_detections)
    assert all(ids == observed_ids[0] and len(ids) == 2*int(has_detection) for ids in observed_ids)
    capture = cv2.VideoCapture(str(output))
    try:
        assert capture.get(cv2.CAP_PROP_FPS) == pytest.approx(10)
        assert capture.get(cv2.CAP_PROP_FRAME_WIDTH) == 96
        assert capture.get(cv2.CAP_PROP_FRAME_HEIGHT) == 64
        decoded = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if has_detection:
                assert frame.max() > 0  # annotations were actually encoded
            decoded += 1
        assert decoded == 23
    finally:
        capture.release()

@pytest.mark.parametrize("guarded", [False, True])
def test_on_pitch_filter_precedes_tracking_classification_and_drawing(tmp_path, monkeypatch, guarded):
    import hashlib
    import json
    import numpy as np
    import cv2
    import supervision as sv
    from backend.cv import team_classifier
    from backend.cv.camera_motion import CameraMotion

    source, output, weights = [tmp_path / n for n in ("in.mp4", "out.mp4", "m.pt")]
    weights.touch()
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (96, 64))
    assert writer.isOpened()
    for _ in range(8):
        writer.write(np.zeros((64, 96, 3), np.uint8))
    writer.release()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps({"source_sha256": digest, "image_size": [96, 64],
        "segments": [{"start_frame": 0, "end_frame": 7,
        "image_points": [[20, 50], [75, 50], [75, 10], [20, 10]],
        "pitch_points": [[0, 0], [105, 0], [105, 68], [0, 68]]}]}))
    # Inside; outside right; torso overlaps pitch but feet below touchline.
    pixels = np.array([[30, 12, 40, 45], [78, 20, 90, 45], [30, 30, 40, 60]], np.float32)
    class Detector:
        names = {0: "person"}
        def __init__(self, *_):
            pass
        def predict(self, *_args, **_kwargs):
            return [SimpleNamespace(boxes=SimpleNamespace(xyxy=SimpleNamespace(
                cpu=lambda: SimpleNamespace(numpy=lambda: pixels))))]
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=Detector))
    monkeypatch.setattr(sv.Detections, "from_ultralytics", staticmethod(lambda _: sv.Detections(
        xyxy=pixels.copy(), confidence=np.full(3, .95), class_id=np.zeros(3, dtype=int))))
    tracker_inputs, drawn, classified = [], [], []
    real_update = sv.ByteTrack.update_with_detections
    def update(self, detections):
        tracker_inputs.append(detections.xyxy.copy())
        return real_update(self, detections)
    monkeypatch.setattr(sv.ByteTrack, "update_with_detections", update)
    real_draw = sv.BoxAnnotator.annotate
    def draw(self, scene, detections, **kwargs):
        drawn.append(detections.xyxy.copy())
        return real_draw(self, scene, detections, **kwargs)
    monkeypatch.setattr(sv.BoxAnnotator, "annotate", draw)
    def classify(frame, box):
        classified.append(box)
        return "A"
    monkeypatch.setattr(team_classifier, "fit_from_samples", lambda *_: SimpleNamespace(predict=classify))
    checks = None
    if guarded:
        def camera(self, image, boxes, anchor=None):
            np.testing.assert_array_equal(boxes, pixels)  # outside people still masked
            if anchor is not None:
                self.matrix = anchor.copy()
            return {"status": "tracked" if self.matrix is not None else "lost"}
        monkeypatch.setattr(CameraMotion, "update", camera)
        checks = tmp_path / "checks.json"
        checks.write_text(json.dumps({"source_sha256": digest, "image_size": [96, 64],
            "max_error_m": .1, "max_gap_frames": 2, "checkpoints": [{"frame": 1,
            "image_points": [[30, 40], [60, 20]],
            "pitch_points": [[10*105/55, 17], [40*105/55, 51]]}]}))
    summary = track_video(source, output, weights, device="cpu", chunk_seconds=.2,
        calibration=calibration, pitch_output=tmp_path / "pitch", team_samples=tmp_path / "samples.json",
        compensate_camera=guarded, landmark_checks=checks, on_pitch_only=True)
    allowed = {1, 2, 3} if guarded else set(range(7))
    # ByteTrack needs confirmation for a new track born after its first frame.
    visible = allowed - {1} if guarded else allowed
    for i, (inputs, boxes) in enumerate(zip(tracker_inputs, drawn)):
        expected = pixels[:1] if i in allowed else np.empty((0, 4), np.float32)
        np.testing.assert_array_equal(inputs, expected)
        expected_drawn = pixels[:1] if i in visible else np.empty((0, 4), np.float32)
        np.testing.assert_array_equal(boxes, expected_drawn)
    assert len(tracker_inputs) == len(drawn) == 8
    assert len(classified) == len(visible)
    assert all(box == pixels[0].tolist() for box in classified)
    # At 10 FPS a track needs three supporting votes before a known role.
    assert summary['team_observations'] == {'A': max(0, len(visible)-2), 'B': 0,
                                            'referee': 0, 'unknown': min(2, len(visible))}
    rows = [json.loads(line) for line in (tmp_path / 'pitch/tracking.jsonl').read_text().splitlines()]
    assert {r['frame'] for r in rows} == visible
    assert len(rows) == len(visible)
    report = json.loads((tmp_path / 'pitch/metrics.json').read_text())
    assert sum(t['samples'] for t in report['tracks']) == len(visible)
    assert report['on_pitch_only'] is True
