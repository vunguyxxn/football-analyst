from backend.cv.ball_sequence import BallContinuity, HandoverCandidates, contact_candidate


def candidate(x, score=.9):
    return {"xyxy": [x - 4, 96, x + 4, 104], "score": score}


def test_ball_requires_consecutive_support_and_never_fills_missing_observations():
    tracker = BallContinuity(1920, 1080, 30)
    assert tracker.update(0, [candidate(100)]) is None
    assert tracker.update(1, [candidate(102)]) is None
    assert tracker.update(2, [candidate(104)])["center_px"] == [104, 100]
    assert tracker.update(3, []) is None
    assert tracker.update(4, [candidate(108)])["gap_frames"] == 1
    assert tracker.update(5, [candidate(110)]) is not None
    assert tracker.update(6, [candidate(112)]) is not None
    assert tracker.update(7, [candidate(500)]) is None
    assert tracker.update(8, [candidate(116)], cut=True) is None


def test_ambiguous_initial_balls_and_nearby_people_are_unknown():
    tracker = BallContinuity(1920, 1080, 30)
    assert tracker.update(0, [candidate(100, .9), candidate(300, .88)]) is None
    ball = {"center_px": [10, 40], "segment": 0}
    people = [{"id": 1, "group": "A", "xyxy": [0, 0, 20, 40]}]
    assert contact_candidate(ball, people)["id"] == 1
    assert contact_candidate(ball, people + [{"id": 2, "group": "A", "xyxy": [2, 0, 22, 40]}]) is None
    assert contact_candidate(None, people) is None


def test_handover_is_only_unverified_with_flight_and_preexisting_recipient():
    engine = HandoverCandidates(10)
    people = [{"id": 1}, {"id": 2}]
    for frame in range(3):
        engine.update(frame, {"segment": 0, "center_px": [0, 0]}, {"id": 1, "group": "A"}, people)
    for frame in (3, 4):
        engine.update(frame, {"segment": 0, "center_px": [30, 0]}, None, people)
    for frame in (5, 6, 7):
        engine.update(frame, {"segment": 0, "center_px": [100, 0]}, {"id": 2, "group": "A"}, people)
    assert len(engine.events) == 1
    assert engine.events[0]["status"] == "unverified"
    assert engine.events[0]["from_id"] == 1 and engine.events[0]["to_id"] == 2


def test_direct_id_swap_or_detection_gap_does_not_become_pass():
    for gap in (False, True):
        engine = HandoverCandidates(10)
        for frame in range(3):
            engine.update(frame, {"segment": 0, "center_px": [0, 0]}, {"id": 1, "group": "A"}, [{"id": 1}, {"id": 2}])
        if gap:
            engine.update(3, None, None, [])
        for frame in (4, 5, 6):
            engine.update(frame, {"segment": 0, "center_px": [100, 0]}, {"id": 2, "group": "A"}, [{"id": 2}])
        assert engine.events == []


def test_long_gap_forces_new_support_before_any_observation():
    tracker = BallContinuity(1920, 1080, 30)
    for frame in (0, 1, 2):
        tracker.update(frame, [candidate(100 + frame)])
    for frame in range(3, 9):
        assert tracker.update(frame, []) is None
    assert tracker.update(9, [candidate(900)]) is None
    assert tracker.update(10, [candidate(901)]) is None
    assert tracker.update(11, [candidate(902)]) is not None


def test_green_region_rejects_bottom_controls_and_requires_touchline():
    import cv2
    import numpy as np
    from backend.cv.ball_sequence import field_region
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame[:] = (40, 130, 50)
    cv2.line(frame, (0, 800), (1919, 780), (255, 255, 255), 4)
    cv2.rectangle(frame, (400, 1000), (1500, 1010), (255, 255, 255), -1)
    region = field_region(frame)
    assert region is not None
    assert cv2.pointPolygonTest(region, (1000., 500.), False) >= 0
    assert cv2.pointPolygonTest(region, (1000., 1000.), False) < 0
    assert field_region(np.full_like(frame, (40, 130, 50))) is None
