import json

import cv2
import numpy as np
import pytest

from backend.cv.pitch_boundary import pitch_region, inside_pitch


def scene():
    image = np.full((540, 960, 3), (45, 135, 50), dtype=np.uint8)
    cv2.line(image, (0, 100), (959, 70), (255, 255, 255), 3)
    cv2.line(image, (0, 450), (959, 390), (255, 255, 255), 3)
    # Parallel painted walkway beyond the playing field must not win by length.
    cv2.line(image, (0, 510), (959, 450), (255, 255, 255), 3)
    # Internal halfway/penalty/centre-circle markings are not outer touchlines.
    cv2.line(image, (400, 87), (500, 419), (255, 255, 255), 3)
    cv2.ellipse(image, (440, 230), (160, 70), 0, 0, 360, (255, 255, 255), 3)
    cv2.line(image, (650, 140), (850, 260), (255, 255, 255), 3)
    return image


def test_white_boundary_rejects_both_green_sides_and_uses_feet_not_box_center():
    region = pitch_region(scene())
    assert region is not None
    assert inside_pitch(region, [300, 150, 340, 300])
    # Body overlaps the playing field, but feet are beyond the near touchline.
    assert not inside_pitch(region, [300, 350, 340, 490])
    assert not inside_pitch(region, [300, 10, 340, 60])
    # Far player's body can extend outside; the footpoint is still on the pitch.
    assert inside_pitch(region, [300, 20, 340, 130])
    assert not inside_pitch(region, [300, 350, 340, 440])


def test_missing_white_lines_has_no_grass_or_previous_frame_fallback():
    assert pitch_region(np.full((540, 960, 3), (45, 135, 50), dtype=np.uint8)) is None
    assert pitch_region(np.zeros((540, 960, 3), dtype=np.uint8)) is None
    assert not inside_pitch(None, [100, 100, 120, 150])
    pitch_region(scene())
    blank = np.full((540, 960, 3), (45, 135, 50), dtype=np.uint8)
    assert pitch_region(blank) is None


def test_pale_technical_walkway_is_not_a_field_of_white_lines():
    image = scene()
    cv2.rectangle(image, (0, 20), (959, 100), (120, 150, 125), -1)
    # Technical dashes above the actual far touchline.
    for x in range(0, 960, 140):
        cv2.line(image, (x, 70), (x + 80, 70), (255, 255, 255), 3)
    cv2.line(image, (0, 105), (959, 105), (170, 190, 175), 3)
    region = pitch_region(image)
    assert region is not None
    assert not inside_pitch(region, [300, 30, 340, 80])
    assert inside_pitch(region, [300, 80, 340, 160])


def test_visible_goal_line_clips_outside_but_penalty_box_does_not():
    image = scene()
    # A goal line meeting the far touchline, unlike an internal penalty-box side.
    cv2.line(image, (750, 76), (959, 200), (255, 255, 255), 3)
    region = pitch_region(image)
    assert region is not None
    assert inside_pitch(region, [760, 130, 780, 180])
    assert not inside_pitch(region, [890, 80, 910, 100])
    assert inside_pitch(region, [700, 250, 720, 300])


@pytest.mark.parametrize("size", [(1920, 1080), (1281, 721)])
def test_boundary_rescales_to_original_pixels(size):
    region = pitch_region(cv2.resize(scene(), size))
    assert region is not None
    scale = np.array([size[0] / 960, size[1] / 540] * 2)
    assert inside_pitch(region, np.array([300, 150, 340, 300]) * scale)
    assert not inside_pitch(region, np.array([300, 350, 340, 490]) * scale)


def test_invalid_boxes_are_not_kept():
    region = pitch_region(scene())
    for box in ([300, 100, 300, 200], [340, 100, 300, 200], [300, 200, 340, 100], [300, 100, 340, float("nan")]):
        assert not inside_pitch(region, box)


def test_cached_filter_changes_only_new_job_and_recounts_every_frame(tmp_path, monkeypatch):
    from backend.cv import filter_job_boundary as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    job = tmp_path / "old"
    job.mkdir()
    (job / "source.mp4").write_bytes(b"source")
    (job / "status.json").write_text(json.dumps({"id": "old", "status": "completed", "result": {
        "frames": 2, "chunks": 1, "width": 960, "height": 540, "fps": 30, "limitations": []}}))
    records = {"frames": [{"frame": i, "time_s": i / 30, "boxes": [
        {"id": 1, "group": "A", "xyxy": [300, 150, 340, 300]},
        {"id": 2, "group": "B", "xyxy": [300, 350, 340, 490]}]} for i in range(2)]}
    original = json.dumps(records)
    (job / "chunk-0.json").write_text(original)

    class Capture:
        index = 0

        def read(self):
            self.index += 1
            return True, scene() if self.index == 1 else np.zeros_like(scene())

        def release(self):
            pass

    monkeypatch.setattr(module.cv2, "VideoCapture", lambda _: Capture())
    output = tmp_path / "new"
    payload = module.filter_job(job, output)
    result = json.loads((output / "chunk-0.json").read_text())["frames"]
    assert [box["id"] for box in result[0]["boxes"]] == [1]
    assert result[1]["boxes"] == [] and result[1]["pitch_boundary"] is None
    assert payload["result"]["observations"] == payload["result"]["track_ids"] == 1
    assert payload["result"]["boundary_filter"]["excluded_observations"] == 3
    assert (job / "chunk-0.json").read_text() == original
    assert not (job / "pitch_estimate").exists()
    assert (output / "source.mp4").read_bytes() == b"source"


def test_upload_filters_before_tracker_and_does_not_publish_unchecked_people(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import supervision as sv
    import torch
    import ultralytics
    from backend.cv import upload_analysis as module
    from backend.cv import team_classifier

    monkeypatch.setattr(module, "video_info", lambda _: {
        "width": 960, "height": 540, "frames": 2, "fps": 30, "duration_s": 2 / 30})
    boxes = np.array([[300, 150, 340, 300], [300, 350, 340, 490], [300, 10, 340, 60]], dtype=float)
    prediction = SimpleNamespace(boxes=SimpleNamespace(xyxy=torch.tensor(boxes)))
    model = SimpleNamespace(names={0: "person"}, predict=lambda *args, **kwargs: [prediction])
    monkeypatch.setattr(ultralytics, "YOLO", lambda _: model)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(team_classifier, "jersey_feature", lambda *args: None)
    monkeypatch.setattr(sv.Detections, "from_ultralytics", staticmethod(lambda _: sv.Detections(
        xyxy=boxes.copy(), confidence=np.ones(3), class_id=np.zeros(3, dtype=int))))
    received = []

    class Tracker:
        def __init__(self, **kwargs):
            pass

        def update_with_detections(self, detections):
            received.append(detections.xyxy.tolist())
            detections.tracker_id = np.ones(len(detections), dtype=int)
            return detections

    class Capture:
        index = 0

        def set(self, key, value):
            self.index = int(value)

        def read(self):
            if self.index >= 2:
                return False, None
            self.index += 1
            return True, scene() if self.index == 1 else np.zeros_like(scene())

        def get(self, key):
            return (self.index - 1) / 30 * 1000

        def release(self):
            pass

    monkeypatch.setattr(sv, "ByteTrack", Tracker)
    monkeypatch.setattr(cv2, "VideoCapture", lambda _: Capture())
    folder = tmp_path / "job"
    folder.mkdir()
    report = module.analyze(tmp_path / "source.mp4", folder, lambda **kwargs: None, lambda: False)
    assert received == [[boxes[0].tolist()], []]
    records = json.loads((folder / "chunk-0.json").read_text())["frames"]
    assert len(records[0]["boxes"]) == 1 and records[1]["boxes"] == []
    assert report["observations"] == 1
    assert report["boundary_filter"]["frames_with_boundary"] == 1
