import numpy as np
import supervision as sv

from backend.cv.track_video import suppress_duplicate_people


def detections(boxes, scores):
    return sv.Detections(xyxy=np.asarray(boxes, dtype=np.float32).reshape(-1, 4),
                         confidence=np.asarray(scores, dtype=np.float32),
                         class_id=np.zeros(len(boxes), dtype=int))


def test_real_duplicate_box_does_not_spawn_another_id():
    # Two YOLO boxes for the same black-shirted player at source frame 1200.
    full = [576.9696, 343.3754, 605.3822, 384.4615]
    duplicate = [577.1669, 343.9047, 594.6830, 385.2039]
    tracker = sv.ByteTrack(frame_rate=60)
    ids = []
    for frame in range(80):
        if 35 <= frame < 40:  # brief detection loss; reappear within buffer
            candidates = detections([], [])
        elif 10 <= frame < 60:
            candidates = detections([full, duplicate], [.554456, .262176])
        else:
            candidates = detections([full], [.554456])
        tracked = tracker.update_with_detections(suppress_duplicate_people(candidates))
        assert len(tracked) == int(not 35 <= frame < 40)
        ids.extend(tracked.tracker_id.tolist())
    assert len(set(ids)) == 1


def test_close_people_are_not_merged_by_pitch_distance():
    # Distinct adjacent people with touching/overlapping boxes, not duplicate boxes.
    # Also preserve a smaller visible person partly obscured by a tall player.
    boxes = [[20, 10, 40, 60], [35, 10, 55, 60], [60, 10, 80, 60], [67, 10, 76, 29]]
    filtered = suppress_duplicate_people(detections(boxes, [.9, .85, .8, .7]))
    assert len(filtered) == 4
    np.testing.assert_array_equal(filtered.xyxy, boxes)
    assert filtered.tracker_id is None
    assert all(filtered.class_id == 0)


def test_empty_detections_can_age_tracker():
    filtered = suppress_duplicate_people(sv.Detections.empty())
    tracked = sv.ByteTrack().update_with_detections(filtered)
    assert len(tracked) == 0
