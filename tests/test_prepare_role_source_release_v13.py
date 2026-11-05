import copy
import json
from pathlib import Path

import pytest

from backend.cv.prepare_role_source_release_v12 import reviewed_regions
from backend.cv.prepare_role_source_release_v13 import validate_supplement

ROOT = Path(__file__).resolve().parents[1]


def packets():
    return [json.loads((ROOT/f'docs/fixtures/role_sources_review_v{v}.json').read_text()) for v in [13,12]]


def test_supplement_covers_two_gaps_in_two_new_scene_groups():
    packet, prior = packets()
    groups = validate_supplement(packet, prior)
    assert groups == {'small_upright_blue_light_keeper':['libertadores_red_stadium_white_black_stripes'],
                      'small_dark_far_assistant':['broadcast_Kobe_Hiroshima']}
    assert packet['training_performed'] is False and packet['role_detector_used_for_selection'] is False


def test_different_minute_of_prior_scene_or_same_pixels_cannot_count_as_new():
    packet, prior = packets()
    packet['sources'][0]['scene_family'] = prior['sources'][0]['scene_family']
    with pytest.raises(ValueError, match='reuses prior'):
        validate_supplement(packet, prior)
    packet, prior = packets()
    packet['sources'][0]['sha256'] = prior['sources'][0]['sha256']
    with pytest.raises(ValueError, match='reuses prior'):
        validate_supplement(packet, prior)


def test_size_threshold_uses_exported_letterbox_not_native_height():
    packet, prior = packets()
    source = packet['sources'][0]
    primary = next(d for d in source['decisions'] if d['source_index']==18)
    primary['xyxy'][3] = primary['xyxy'][1]+72  # Exactly24px at640 is outside strict<24.
    with pytest.raises(ValueError, match='truly small'):
        validate_supplement(packet, prior)


def test_lying_and_enlarged_tight_crops_do_not_cover_upright_small_gap():
    packet, prior = packets()
    packet['primary_observations'][0]['pose'] = 'lying'
    with pytest.raises(ValueError, match='Lying/seated'):
        validate_supplement(packet, prior)
    packet, prior = packets()
    packet['sources'][0]['regions'][0]['roi'][2] = 1000
    with pytest.raises(ValueError, match='native wide'):
        validate_supplement(packet, prior)


def test_wrong_color_or_omitted_prior_release_is_rejected():
    packet, prior = packets()
    packet['primary_observations'][1]['shirt_color'] = 'red'
    with pytest.raises(ValueError, match='requested gap'):
        validate_supplement(packet, prior)
    packet, prior = packets()
    packet['additional_references'] = []
    with pytest.raises(ValueError, match='v12 release'):
        validate_supplement(packet, prior)


def test_all_source_boxes_accounted_for_and_partial_bottom_actor_excluded_by_roi():
    packet, _ = packets()
    counts = {'player':0,'goalkeeper':0,'referee':0}
    for source in packet['sources']:
        lines = []
        w,h = source['width'],source['height']
        for d in source['decisions']:
            a,b,c,e = d['xyxy']
            lines.append(f'{d["source_class"]} {(a+c)/2/w:.15f} {(b+e)/2/h:.15f} {(c-a)/w:.15f} {(e-b)/h:.15f}')
        regions = reviewed_regions(copy.deepcopy(source), '\n'.join(lines)+'\n')
        assert len(regions)==1 and not regions[0]['negative']
        for obj in regions[0]['objects']:
            counts[obj['role']] += 1
        if source['id']=='v13-88':
            assert source['decisions'][12]['action']=='outside_review'
            assert source['decisions'][12]['xyxy'][1] > 920
    assert counts == {'player':33,'goalkeeper':2,'referee':4}
