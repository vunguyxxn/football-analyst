import copy
import json
from pathlib import Path

import pytest

from backend.cv.audit_role_errors_v11 import fp_transitions, keeper_false_positives, validate_review
from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import match


def box(identifier, role, x=10):
    return {'id': identifier, 'role': role, 'xyxy': [x, 10, x+20, 60]}


def test_fp_rows_include_wrong_role_matches_and_unmatched_duplicate_boxes():
    labels = [box(0, 'player'), box(1, 'goalkeeper', 100)]
    predictions = [box(0, 'goalkeeper'), box(1, 'goalkeeper', 100),
                   box(2, 'goalkeeper', 101), box(3, 'goalkeeper', 300)]
    rows = keeper_false_positives(labels, predictions, match(labels, predictions))
    assert [r['mechanism'] for r in rows] == ['matched_wrong_role', 'unmatched_gt_assigned_elsewhere', 'unmatched_no_gt_iou50']
    assert len(rows) == operating_metrics(*frame_confusion(labels, predictions))['classes']['goalkeeper']['fp']
    assert rows[1]['overlapping_labels'][0]['assigned_prediction']['id'] == 1


def test_cross_role_competition_keeps_scored_fp_even_if_person_is_a_keeper():
    labels = [box(0, 'goalkeeper')]
    predictions = [box(0, 'player'), box(1, 'goalkeeper', 11)]
    rows = keeper_false_positives(labels, predictions, match(labels, predictions))
    assert len(rows) == 1
    assert rows[0]['assigned_label'] is None
    assert rows[0]['coincident_predictions'][0]['role'] == 'player'
    assert rows[0]['mechanism'] == 'unmatched_gt_assigned_elsewhere'


def test_fp_transition_uses_spatial_matching_not_prediction_ids_or_count_delta():
    before = [{'xyxy': [0, 0, 10, 20]}, {'xyxy': [100, 0, 110, 20]}]
    after = [{'xyxy': [1, 0, 11, 20]}, {'xyxy': [200, 0, 210, 20]}]
    changes, removed = fp_transitions(before, after)
    assert [x['transition'] for x in changes] == ['retained_fp', 'new_fp']
    assert removed == 1  # Equal totals do not mean no new/resolved errors.
    assert fp_transitions([], after)[1] == 0
    assert fp_transitions(before, [])[1] == 2


def reviewed_packet():
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root/'docs/fixtures/role_error_audit_review_v11.json').read_text())
    audit = {'manifest_sha256': review['manifest_sha256'], 'weights': review['weights'],
             'keeper_fp_rows': copy.deepcopy(review['keeper_predictions']),
             'referee_fn_rows': copy.deepcopy(review['referee_labels'])}
    return audit, review


def test_review_must_cover_every_scored_error_without_changing_diagnostics():
    audit, review = reviewed_packet()
    assert validate_review(audit, review) == {'keeper_rows': 49, 'referee_rows': 149}
    review['keeper_predictions'].pop()
    with pytest.raises(ValueError, match='coverage'):
        validate_review(audit, review)
    audit, review = reviewed_packet()
    review['referee_labels'][0]['raw_v11']['best']['scores']['referee'] = 1.
    with pytest.raises(ValueError, match='evidence'):
        validate_review(audit, review)


def test_review_cannot_change_thresholds_weights_or_claim_independent_validation():
    for field, value in [('confidence', .1), ('independently_validated', True), ('manifest_sha256', 'other')]:
        audit, review = reviewed_packet()
        review[field] = value
        with pytest.raises(ValueError):
            validate_review(audit, review)
