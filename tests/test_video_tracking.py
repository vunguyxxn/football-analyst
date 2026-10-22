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
@pytest.mark.parametrize("pitch_mode", [True, False, "moving"])
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
    summary = track_video(source, output, weights, device="cpu", chunk_seconds=0.5,
                          team_samples=tmp_path / "samples.json" if team_mode else None,
                          calibration=calibration if pitch_mode else None,
                          pitch_output=tmp_path / "pitch" if pitch_mode else None,
                          compensate_camera=pitch_mode == "moving")
    from backend.common.schemas import TrackingRow
    if pitch_mode:
        rows = [TrackingRow.model_validate_json(line) for line in
                (tmp_path / "pitch/tracking.jsonl").read_text().splitlines()]
        assert len(rows) == (2 if pitch_mode == "moving" else 46)*int(has_detection)
        assert summary["projected_rows"] == len(rows)
        assert all(0 <= row.x_m <= 105 and 0 <= row.y_m <= 68 for row in rows)
        report = json.loads((tmp_path / "pitch/metrics.json").read_text())
        assert len(report["tracks"]) == 2*int(has_detection)
        assert all(track["distance_m"] == 0 for track in report["tracks"])
        if pitch_mode == "moving":
            quality = [json.loads(line) for line in (tmp_path / "pitch/camera_quality.jsonl").read_text().splitlines()]
            assert len(quality) == 23
            assert quality[0]["status"] == "manual_anchor"
            assert all(item["status"] == "lost" for item in quality[1:])
    else:
        assert "pitch_output" not in summary
        assert not (tmp_path / "pitch").exists()
    if team_mode:
        assert summary["team_observations"] == (
            {"A": 12, "B": 12, "referee": 11, "unknown": 11} if has_detection
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
