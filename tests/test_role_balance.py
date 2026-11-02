import copy

import pytest

from backend.cv.balance_role_dataset import crop_labels, protected_rows, repeat_count
from backend.cv.compare_role_models import frame_confusion, operating_metrics, validation_choice


POLICY = {"referee_color_repeats": {"light_blue": 1, "yellow": 3, "red": 6, "black": 6},
          "player_hard_negative_repeats": 1, "staff_background_repeats": 2, "maximum_repeats": 6}


def test_repeat_weights_are_explicit_capped_and_preserve_negatives():
    region = {"review_status": "agent_reviewed", "kind": "referee", "attributes": {"shirt_color": "black"}}
    assert repeat_count(region, POLICY) == 6
    region["kind"] = "player_hard_negative"
    assert repeat_count(region, POLICY) == 1
    region["kind"] = "staff_background"
    assert repeat_count(region, POLICY) == 2


@pytest.mark.parametrize("bad", [0, 7, True, 1.5])
def test_invalid_repeat_policy_fails(bad):
    policy = copy.deepcopy(POLICY)
    policy["referee_color_repeats"]["black"] = bad
    with pytest.raises(ValueError, match="cap"):
        repeat_count({"review_status": "agent_reviewed", "kind": "referee", "attributes": {"shirt_color": "black"}}, policy)


def test_unreviewed_positive_cannot_be_oversampled():
    with pytest.raises(ValueError, match="Unreviewed"):
        repeat_count({"review_status": "pending"}, POLICY)


def test_crop_label_uses_roi_coordinates_and_retains_context_role():
    region = {"roi": [100, 200, 200, 300], "objects": [
        {"role": "referee", "xyxy": [110, 220, 150, 280]},
        {"role": "player", "xyxy": [180, 200, 200, 250]}]}
    rows = [line.split() for line in crop_labels(region).splitlines()]
    assert rows[0][0] == "2"
    assert list(map(float, rows[0][1:])) == pytest.approx([.3, .5, .4, .6])
    assert rows[1][0] == "0"
    assert list(map(float, rows[1][1:])) == pytest.approx([.9, .25, .2, .5])
    assert crop_labels({"roi": [0, 0, 20, 20], "objects": []}) == ""


def test_unlabelled_pixels_outside_roi_cannot_enter_export():
    with pytest.raises(ValueError, match="outside"):
        crop_labels({"roi": [10, 10, 20, 20], "objects": [{"role": "referee", "xyxy": [9, 10, 20, 20]}]})


def test_protected_split_comparison_ignores_train_and_detects_test_mutation():
    record = {"split": "test", "image": "test.png", "image_sha256": "imagehash", "label": "test.txt", "label_sha256": "labelhash"}
    before = {"files": [record]}
    after = {"files": [{**record, "split": "train"}, dict(record)]}
    assert protected_rows(before) == protected_rows(after)
    after["files"][1]["label_sha256"] = "changed"
    assert protected_rows(before) != protected_rows(after)


def test_role_confusion_is_spatially_matched_before_scoring():
    counts, extras = frame_confusion([{"role": "referee", "xyxy": [0, 0, 10, 20]}], [
        {"role": "player", "xyxy": [0, 0, 10, 20]},
        {"role": "referee", "xyxy": [1, 0, 11, 20]}])
    result = operating_metrics(counts, extras)
    assert result["nonplayers_called_player"] == 1
    assert result["classes"]["referee"] == {"tp": 0, "fp": 1, "fn": 1, "precision": 0., "recall": 0.}
    assert result["classes"]["player"]["fp"] == 1


def test_extra_predictions_and_misses_are_not_hidden():
    counts, extras = frame_confusion([{"role": "referee", "xyxy": [0, 0, 10, 20]},
                                     {"role": "goalkeeper", "xyxy": [100, 0, 110, 20]}], [
        {"role": "referee", "xyxy": [0, 0, 10, 20]},
        {"role": "referee", "xyxy": [200, 0, 210, 20]}])
    result = operating_metrics(counts, extras)
    assert result["classes"]["referee"]["precision"] == .5
    assert result["classes"]["goalkeeper"]["fn"] == 1


@pytest.mark.parametrize("change", ["referee", "player", "goalkeeper", "overall"])
def test_validation_improvement_cannot_hide_role_or_overall_regression(change):
    baseline = {"map50_95": .5, "classes": {role: {"map50": .5} for role in ["player", "goalkeeper", "referee"]}}
    candidate = copy.deepcopy(baseline)
    candidate["classes"]["referee"]["map50"] = .6
    if change == "overall":
        candidate["map50_95"] = .4
    else:
        candidate["classes"][change]["map50"] = .3
    gate = {"referee_map50_gain_min": .05, "overall_map50_95_drop_max": .03, "player_map50_drop_max": .03, "goalkeeper_map50_drop_max": .05}
    assert validation_choice(baseline, candidate, gate)["preferred_by_validation"] == "baseline"


def test_validation_gate_handles_float_threshold_without_reading_test():
    baseline = {"map50_95": .5, "classes": {role: {"map50": .2} for role in ["player", "goalkeeper", "referee"]}}
    candidate = copy.deepcopy(baseline)
    candidate["classes"]["referee"]["map50"] = .25
    gate = {"referee_map50_gain_min": .05, "overall_map50_95_drop_max": .03, "player_map50_drop_max": .03, "goalkeeper_map50_drop_max": .05}
    assert validation_choice(baseline, candidate, gate)["preferred_by_validation"] == "balanced"
