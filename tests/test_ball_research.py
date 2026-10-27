import pytest
from backend.cv.ball_probe import merge_candidates
from backend.cv.finetune_ball import ball_labels, ball_validator_class
from backend.cv.evaluate_ball_probe import evaluate


def test_ball_labels_keep_only_original_ball_and_reject_corruption():
    assert ball_labels("0 .5 .5 .01 .02\n2 .3 .4 .1 .2\n3 .1 .1 .1 .1\n") == "0 .5 .5 .01 .02\n"
    assert ball_labels("1 .5 .5 .1 .2\n") == ""
    with pytest.raises(ValueError):
        ball_labels("0 nan .5 .1 .1")


def test_candidate_merge_preserves_strongest_overlapping_crop_and_distinct_ball():
    inputs = [{"xyxy": [0, 0, 10, 10], "score": .2},
              {"xyxy": [1, 1, 11, 11], "score": .8},
              {"xyxy": [30, 30, 40, 40], "score": .4},
              {"xyxy": [0, 0, 0, 0], "score": .99}]
    merged = merge_candidates(inputs)
    assert [item["score"] for item in merged] == [.8, .4]


def test_baseline_validator_filters_coco_ball_before_nms_and_remaps_class():
    import torch
    from types import SimpleNamespace
    # Coincident high-confidence person must not suppress lower-confidence ball.
    predictions = torch.zeros((1, 84, 2))
    predictions[0, :4, :] = torch.tensor([[100, 100], [100, 100], [20, 20], [20, 20]])
    predictions[0, 4, 0] = .99
    predictions[0, 4 + 32, 1] = .8
    validator = ball_validator_class(32).__new__(ball_validator_class(32))
    validator.args = SimpleNamespace(conf=.01, iou=.7, task="detect", max_det=300)
    validator.end2end = False
    result = validator.postprocess(predictions)[0]
    assert result["bboxes"].shape[0] == 1
    assert result["cls"].tolist() == [0]
    assert result["conf"][0].item() == pytest.approx(.8)


def test_sparse_review_skips_uncertain_frames_and_counts_extra_false_candidates():
    predictions = {"source_sha256": "same", "samples": [
        {"frame": 0, "candidates": [{"score": .8, "xyxy": [8, 8, 12, 12]}, {"score": .7, "xyxy": [80, 80, 90, 90]}]},
        {"frame": 1, "candidates": []}, {"frame": 2, "candidates": []}]}
    review = {"source_sha256": "same", "score_threshold": .1, "center_tolerance_px": 3, "scope": "not ground truth", "frames": [
        {"frame": 0, "visibility": "visible", "center": [10, 10]},
        {"frame": 1, "visibility": "visible", "center": [10, 10]},
        {"frame": 2, "visibility": "uncertain", "center": None}]}
    metrics = evaluate(predictions, review)
    assert (metrics["point_matches"], metrics["unmatched_candidates"], metrics["missed_visible_points"]) == (1, 1, 1)
    assert metrics["scored_frames"] == 2 and metrics["uncertain_frames_skipped"] == 1
    assert metrics["precision_proxy"] == .5 and metrics["recall_proxy"] == .5
    with pytest.raises(ValueError):
        evaluate({**predictions, "source_sha256": "other"}, review)
