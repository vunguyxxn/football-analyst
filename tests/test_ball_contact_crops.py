from collections import deque
from types import SimpleNamespace

import numpy as np

from backend.cv.ball_contact_crops import contact_crops, merge_candidates, refine_candidates


def test_crops_require_recent_observed_ball_near_player_and_stay_bounded():
    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    people = [{"xyxy": [10, 0, 50, 70]}]
    history = deque([(10, np.array([30, 65]))])
    assert contact_crops(frame, people, [], 11, 30) == []
    assert contact_crops(frame, people, history, 20, 30) == []
    crops = contact_crops(frame, people, history, 11, 30)
    assert len(crops) == 1 and crops[0][1:] == (0, 0)
    assert crops[0][0].shape[0] <= 320 and crops[0][0].shape[1] <= 320
    assert contact_crops(frame, [{"xyxy": [800, 400, 830, 500]}], history, 11, 30) == []


def test_crop_detection_translates_back_to_original_pixels_and_empty_is_not_imputed():
    class Tensor:
        def __init__(self, value): self.value = np.asarray(value)
        def cpu(self): return self
        def numpy(self): return self.value

    class Model:
        def predict(self, images, **kwargs):
            assert kwargs["imgsz"] == 640 and kwargs["conf"] == .25
            return [SimpleNamespace(boxes=SimpleNamespace(xyxy=Tensor([[1, 2, 9, 10]]), conf=Tensor([.8]))) for _ in images]

    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    people = [{"xyxy": [400, 200, 440, 300]}]
    history = deque([(10, np.array([420, 300]))])
    candidates, queries = refine_candidates(Model(), frame, people, history, 11, 30, "cpu")
    crop = contact_crops(frame, people, history, 11, 30)[0]
    assert queries == 1
    assert candidates[0]["xyxy"] == [crop[1]+1, crop[2]+2, crop[1]+9, crop[2]+10]
    assert refine_candidates(Model(), frame, people, history, 20, 30, "cpu") == ([], 0)


def test_merge_drops_duplicate_proposals_before_ambiguity_check():
    kept = merge_candidates([{"xyxy": [10, 10, 20, 20], "score": .5},
                             {"xyxy": [11, 10, 21, 20], "score": .8},
                             {"xyxy": [100, 100, 110, 110], "score": .7}])
    assert len(kept) == 2 and kept[0]["score"] == .8
