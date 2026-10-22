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
def test_video_round_trip_preserves_ids_across_chunks(tmp_path, monkeypatch, has_detection):
    """Use real codec and ByteTrack with deterministic detector boxes."""
    cv2 = pytest.importorskip("cv2")
    sv = pytest.importorskip("supervision")
    np = pytest.importorskip("numpy")
    source, output, weights = [tmp_path / name for name in ("in.mp4", "out.mp4", "m.pt")]
    weights.touch()
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (96, 64))
    assert writer.isOpened()
    for _ in range(23):
        writer.write(np.zeros((64, 96, 3), dtype=np.uint8))
    writer.release()
    observed_ids = []
    real_update = sv.ByteTrack.update_with_detections

    def update(tracker, detections):
        result = real_update(tracker, detections)
        observed_ids.append(result.tracker_id.tolist())
        return result

    class Detector:
        names = {0: "person"}

        def __init__(self, path):
            pass

        def predict(self, frame, **kwargs):
            assert kwargs["classes"] == [0]
            return [object()]

    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=Detector))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setattr(sv.ByteTrack, "update_with_detections", update)
    monkeypatch.setattr(sv.Detections, "from_ultralytics", staticmethod(lambda _: (
        sv.Detections(
            xyxy=np.array([[20, 10, 40, 50]], dtype=np.float32),
            confidence=np.array([0.95], dtype=np.float32), class_id=np.array([0]),
        ) if has_detection else sv.Detections.empty()
    )))
    summary = track_video(source, output, weights, device="cpu", chunk_seconds=0.5)
    assert summary["frames"] == 23
    assert summary["chunks"] == 5
    assert len(observed_ids) == 23
    assert all(ids == observed_ids[0] and len(ids) == int(has_detection) for ids in observed_ids)
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
