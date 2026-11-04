import copy
import pytest

from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.offline_role_dedup_v11 import evaluate_frames


def fixture(role):
    label = {'id': 7, 'role': role, 'xyxy': [0, 0, 20, 40]}
    predictions = [{'id': 0, 'role': 'player', 'xyxy': [0, 0, 20, 40], 'confidence': .6},
                   {'id': 1, 'role': 'referee', 'xyxy': [1, 0, 21, 40], 'confidence': .9}]
    frame = {'image': 'images/val/a.png', 'image_sha256': 'i', 'label_sha256': 'l',
             'labels': [label], 'predictions': predictions}
    expected = {**operating_metrics(*frame_confusion([label], predictions)), 'frames': 1}
    return frame, expected


def test_referee_can_gain_tp_when_player_box_won_original_greedy_matching():
    frame, expected = fixture('referee')
    old = copy.deepcopy(frame)
    report, changes, events = evaluate_frames([frame], expected)
    assert report['original']['classes']['referee']['tp'] == 0
    assert report['deduplicated']['classes']['referee']['tp'] == 1
    assert report['transitions']['referee'] == {'gained': 1}
    assert changes[0]['label_id'] == 7 and changes[0]['transition'] == 'gained'
    assert events[0]['suppressed'] == [{'removed_index': 0, 'winner_index': 1}]
    assert frame == old


def test_false_positive_reduction_does_not_hide_lost_player_tp():
    frame, expected = fixture('player')
    report, changes, _ = evaluate_frames([frame], expected)
    assert report['original']['classes']['player']['tp'] == 1
    assert report['deduplicated']['classes']['player']['tp'] == 0
    assert report['transitions']['player'] == {'lost': 1}
    assert changes[0]['after']['role'] == 'referee'
    assert report['removed'] == 1


def test_all_class_baseline_and_frame_count_must_match_frozen_reference():
    frame, expected = fixture('goalkeeper')
    for changed in [dict(expected, frames=2), copy.deepcopy(expected)]:
        if changed['frames'] == 1:
            changed['classes']['player']['fp'] += 1
        with pytest.raises(ValueError, match='baseline'):
            evaluate_frames([frame], changed)
