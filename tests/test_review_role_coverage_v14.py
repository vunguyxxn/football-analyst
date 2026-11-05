import copy
import json
from pathlib import Path

import pytest

from backend.cv.review_role_coverage_v14 import choose_parents, group_counts, heights, validate_review

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packet():
    review = json.loads((ROOT / 'docs/fixtures/role_coverage_review_v14.json').read_text())
    lock = json.loads((ROOT / 'docs/fixtures/role_coverage_review_plan_v14.json').read_text())
    inventory = {'objects': copy.deepcopy(review['objects']), 'parents': {
        p['parent']: {'family': p['family'], 'units': p['unit_ids']} for p in review['parents']}}
    return inventory, lock, review


def test_sampling_is_deterministic_and_includes_new_parents_without_repeats():
    counts = {'red_stadiums': 8, 'euro_red_white': 4,
              'soccertrack-match-117093': 3, 'soccertrack-match-118575': 3}
    parents = {f'{family}:{i}': {'family': family} for family, n in counts.items() for i in range(n)}
    parents['new'] = {'family': 'new-family'}
    a = choose_parents(parents, {'new'})
    assert len(a) == 9 and 'new' in a
    assert a == choose_parents(dict(reversed(list(parents.items()))), {'new'})


def test_letterbox_size_uses_loaded_crop_and_original_source_separately():
    h = heights([100, 200, 120, 258], [90, 190, 153, 253], 1920, 1080)
    assert h['source_height640'] == pytest.approx(58 * 640 / 1920)
    assert h['loaded_height640'] == pytest.approx(58 * 640 / 63)
    assert h['source_height1280'] == 2 * h['source_height640']
    assert h['loaded_height1280'] == 2 * h['loaded_height640']


def test_invalid_geometry_is_not_silently_counted():
    with pytest.raises(ValueError, match='geometry'):
        heights([0, 2, 1, 1], [0, 0, 30, 30], 1920, 1080)


def test_counts_do_not_equate_exposures_to_parents():
    assert group_counts([{'parent': 'p', 'family': 'f', 'exposures': 4}] * 2) == {
        'unit_boxes': 2, 'parent_frames': 1, 'families': {'f': 2}, 'box_exposures': 8}


def test_review_packet_is_complete_pending_and_frozen(packet):
    j, lock, review = packet
    assert len(validate_review(j, lock, review)) == 327
    assert len(lock['parent_sample']) == 21


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'geometry', 'parent_roi', 'acceptance', 'applied', 'class_geometry'])
def test_mutated_review_cannot_pass_frozen_evidence(packet, mutation):
    j, lock, review = packet
    if mutation == 'missing': review['objects'].pop()
    elif mutation == 'duplicate': review['objects'][-1] = copy.deepcopy(review['objects'][0])
    elif mutation == 'geometry': review['objects'][0]['xyxy'][0] += 1
    elif mutation == 'parent_roi': review['parents'][0]['unit_ids'] = []
    elif mutation == 'acceptance': review['independently_validated'] = True
    elif mutation == 'applied': review['label_proposals'][0]['applied'] = True
    elif mutation == 'class_geometry': review['label_proposals'][1]['proposed_label_line'] = '1 0.5 0.5 0.2 0.2'
    with pytest.raises(ValueError):
        validate_review(j, lock, review)
