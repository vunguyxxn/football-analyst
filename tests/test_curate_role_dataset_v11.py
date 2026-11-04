import copy
import json
from pathlib import Path

import pytest

from backend.cv.curate_role_dataset_v11 import amend, clean_rows, validate_source, write_summary


def correction():
    return {'image': 'images/train/a.png', 'image_sha256': 'i', 'label_sha256': 'l',
            'pixel_sha256': 'p', 'action': 'relabel', 'line_index': 1,
            'from_class': '1', 'to_class': '2'}


def base():
    return {'files': [{'image': 'images/train/a.png', 'image_sha256': 'i',
                      'label_sha256': 'l', 'pixel_sha256': 'p', 'split': 'train'}]}


def test_single_token_correction_preserves_coordinates_and_crlf():
    text = '0 .1 .2 .3 .4\r\n1 .5 .6 .7 .8\r\n2 .2 .3 .4 .5\r\n'
    assert amend(text, correction()) == text.replace('1 .5', '2 .5')
    for change in [dict(correction(), line_index=0), dict(correction(), line_index=99)]:
        with pytest.raises(ValueError):
            amend(text, change)


def test_quarantine_removes_whole_frame_including_repeated_pixels():
    data = base()
    data['files'].append(dict(data['files'][0], image='images/train/repeat.png'))
    rows, quarantined, corrected = clean_rows(data, [dict(correction(), action='quarantine')])
    assert not rows and len(quarantined) == 2 and not corrected


def test_corrections_cannot_reach_protected_pixels_or_unreviewed_labels():
    data = base()
    data['files'].append(dict(data['files'][0], image='images/val/a.png', split='val'))
    with pytest.raises(ValueError, match='protected'):
        clean_rows(data, [correction()])
    data['files'][1].update(split='train', label_sha256='other')
    with pytest.raises(ValueError, match='alternate labels'):
        clean_rows(data, [correction()])
    with pytest.raises(ValueError, match='hash'):
        clean_rows(base(), [dict(correction(), label_sha256='changed')])


def packet():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root/'docs/fixtures/role_sources_review_v11.json').read_text())


def lock(source):
    return {k: source[k] for k in ['id', 'scene_family', 'split', 'sha256', 'roi']}


def test_new_sources_have_reviewed_three_role_labels_and_true_small_examples():
    sources = packet()['sources']
    assert len(sources) == 5
    assert len({s['scene_family'] for s in sources}) == 4
    groups = set()
    for source in sources:
        text = validate_source(source, lock(source))
        assert len(text.splitlines()) == len(source['objects'])
        primary = next(o for o in source['objects'] if o['id'] == source['primary_id'])
        size = (primary['xyxy'][3]-primary['xyxy'][1])*640/max(source['roi'][2],source['roi'][3])
        if size < 24:
            groups.add((primary['role'], source['primary_color']))
    assert {('goalkeeper', 'blue_cyan'), ('goalkeeper', 'light_gray_white'), ('referee', 'dark')} <= groups


def test_uncertain_context_duplicate_boxes_and_class_mapping_are_rejected():
    original = packet()['sources'][0]
    source = copy.deepcopy(original)
    source['uncertain_boxes'] = [{'xyxy': source['objects'][0]['xyxy']}]
    with pytest.raises(ValueError, match='background'):
        validate_source(source, lock(original))
    source = copy.deepcopy(original)
    source['objects'].append(dict(source['objects'][0], id='duplicate'))
    with pytest.raises(ValueError, match='Duplicate actor'):
        validate_source(source, lock(original))
    source = copy.deepcopy(original)
    source['objects'][0]['role'] = 'referee'
    with pytest.raises(ValueError, match='mapping'):
        validate_source(source, lock(original))


def test_source_split_and_geometry_stay_locked():
    source = copy.deepcopy(packet()['sources'][0])
    frozen = lock(source)
    source['roi'] = [0, 0, 1000, 1000]
    with pytest.raises(ValueError, match='identity'):
        validate_source(source, frozen)
    source['split'] = 'heldout_review'
    with pytest.raises(ValueError, match='train'):
        validate_source(source, frozen)


def test_summary_accepts_legacy_rows_without_sampling_origin(tmp_path):
    protocol = tmp_path/'protocol.json'
    protocol.write_text(json.dumps({'dataset': 'dataset'}))
    (tmp_path/'dataset').mkdir()
    (tmp_path/'dataset/manifest.json').write_text('{}')
    (tmp_path/'docs/fixtures').mkdir(parents=True)
    legacy = {'split': 'train', 'pixel_sha256': 'old', 'label_sha256': 'old', 'class_counts': {'1': 2}}
    added = dict(legacy, pixel_sha256='new', sampling_origin='reviewed_wide_context_v11', class_counts={'2': 1})
    result = {'files': [legacy, added], 'images': {'train': 2}, 'v11_quarantined': [],
              'v11_corrected': [], 'v11_new_images': 1}
    summary = write_summary(tmp_path, protocol, result, {'sources': [{'scene_family': 'new'}]}, [], 3)
    assert summary['new_box_counts'] == {2: 1}
    assert summary['train_unit_count'] == 2
