import copy
import json
from pathlib import Path

import pytest

from backend.cv.prepare_role_source_release_v12 import reviewed_regions


ROOT = Path(__file__).resolve().parents[1]


def source_case():
    text = '1 0.25 0.5 0.1 0.2\n2 0.75 0.5 0.1 0.2\n'
    source = {'split': 'train', 'review_status': 'agent_reviewed', 'width': 1000, 'height': 500,
              'uncertain_boxes': [], 'decisions': [
                  {'source_index': 0, 'source_class': 1, 'xyxy': [200,200,300,300], 'action': 'target', 'role': 'goalkeeper', 'reason': 'Upright at goal'},
                  {'source_index': 1, 'source_class': 2, 'xyxy': [700,200,800,300], 'action': 'target', 'role': 'referee', 'reason': 'Far assistant with flag'}],
              'regions': [{'id':'field', 'roi':[0,0,1000,500], 'negative':False, 'coverage_reviewed':True, 'background_types':[]},
                          {'id':'roof', 'roi':[0,0,1000,150], 'negative':True, 'coverage_reviewed':True, 'background_types':['floodlights']}]}
    return source, text


def test_background_exports_empty_yolo_label_without_dropping_active_roles():
    source, text = source_case()
    regions = reviewed_regions(source, text)
    assert [o['role'] for o in regions[0]['objects']] == ['goalkeeper','referee']
    assert len(regions[0]['labels'].splitlines()) == 2
    assert regions[1]['labels'] == '' and regions[1]['objects'] == []


def test_negative_roi_cannot_contain_target_or_unreviewed_actor():
    source, text = source_case()
    source['regions'][1]['roi'] = [0,0,500,400]
    with pytest.raises(ValueError, match='Negative ROI'):
        reviewed_regions(source, text)
    source['decisions'][0]['action'] = 'outside_review'
    with pytest.raises(ValueError, match='Unreviewed source actor'):
        reviewed_regions(source, text)


def test_partial_targets_and_uncertain_actors_are_rejected():
    source, text = source_case()
    source['regions'][0]['roi'][2] = 750
    with pytest.raises(ValueError):
        reviewed_regions(source, text)
    source, text = source_case()
    source['uncertain_boxes'] = [[5,5,10,10]]
    with pytest.raises(ValueError, match='Uncertain actor'):
        reviewed_regions(source, text)


def test_source_ledger_cannot_omit_or_change_original_geometry_or_class():
    source, text = source_case()
    source['decisions'].pop()
    with pytest.raises(ValueError, match='Incomplete'):
        reviewed_regions(source, text)
    source, text = source_case()
    source['decisions'][0]['xyxy'][0] += 1
    with pytest.raises(ValueError, match='geometry'):
        reviewed_regions(source, text)
    source, text = source_case()
    source['decisions'][0]['role'] = 'referee'
    with pytest.raises(ValueError, match='role mapping'):
        reviewed_regions(source, text)


def test_committed_packet_has_new_upright_and_dark_far_groups_and_explicit_repairs():
    packet = json.loads((ROOT/'docs/fixtures/role_sources_review_v12.json').read_text())
    assert packet['training_performed'] is False
    sources = packet['sources']
    assert len(sources) == 6 and len({s['scene_family'] for s in sources}) == 5
    repairs = {(s['survey_id'],d['source_index']) for s in sources for d in s['decisions'] if d['action']=='discard'}
    assert repairs == {(29,14),(25,19),(151,16)}
    far = [o for o in packet['primary_observations'] if o['location']=='far_touchline']
    assert len(far) == 2 and {o['shirt_color'] for o in far} == {'dark'}
    assert {o['source_id'] for o in far} == {'v12-79','v12-186'}
    groups = {s['id']:s['scene_family'] for s in sources}
    assert len({groups[o['source_id']] for o in far}) == 1  # Two times, not two matches.


def test_packet_labels_replay_from_exact_source_geometry_without_local_assets():
    packet = json.loads((ROOT/'docs/fixtures/role_sources_review_v12.json').read_text())
    counts = {'player':0,'goalkeeper':0,'referee':0}
    negative = positive = 0
    for source in packet['sources']:
        # Reconstruct source YOLO solely to exercise every reviewed ledger/ROI in CI.
        lines = []
        w,h = source['width'],source['height']
        for d in source['decisions']:
            a,b,c,e = d['xyxy']
            lines.append(f'{d["source_class"]} {(a+c)/2/w:.15f} {(b+e)/2/h:.15f} {(c-a)/w:.15f} {(e-b)/h:.15f}')
        regions = reviewed_regions(copy.deepcopy(source), '\n'.join(lines)+'\n')
        for r in regions:
            negative += r['negative']; positive += not r['negative']
            for obj in r['objects']:
                counts[obj['role']] += 1
    assert (positive,negative) == (4,3)
    assert counts == {'player':52,'goalkeeper':4,'referee':6}
