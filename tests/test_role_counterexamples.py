import copy
import json
from pathlib import Path

import numpy as np
import pytest

from backend.cv.curate_role_counterexamples import duplicate_hits, git_blob_sha, validate, validate_region
from backend.cv.evaluate_role_detector import digest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def packet(tmp_path):
    data = json.loads((ROOT / 'docs/fixtures/role_counterexamples_v3.json').read_text(encoding='utf-8'))
    protected = tmp_path / 'protected'
    protected.mkdir()
    manifest = protected / 'manifest.json'
    manifest.write_text(json.dumps({'files': [{'family': 'protected_match'}]}))
    data['protected_dataset'] = 'protected'
    data['protected_manifest_sha256'] = digest(manifest)
    return tmp_path, data


def audit(packet, **kwargs):
    root, data = packet
    path = root / 'packet.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return validate(root, path, **kwargs)


def test_packet_counts_are_observations_not_training_or_independent_evaluation(packet):
    result = audit(packet)
    assert result['sources'] == 11
    assert result['reviewed_regions'] == 58
    assert result['primary_counts'] == {'player/yellow': 39, 'referee/yellow': 4,
                                       'referee/turquoise': 13, 'referee/pink': 1, 'goalkeeper/yellow': 1}
    assert result['prior_images_screened'] == 0
    assert result['prior_duplicate_hits'] is None
    assert not result['training_performed']
    assert not result['independently_validated']


@pytest.mark.parametrize('field,value', [('split', 'val'), ('scene_family', 'protected_match'),
                                       ('media_kind', 'simulation'), ('origin_path', 'images/PES_21_clip.jpg')])
def test_protected_or_simulated_sources_rejected(packet, field, value):
    packet[1]['sources'][0][field] = value
    with pytest.raises(ValueError):
        audit(packet)


@pytest.mark.parametrize('field,value', [('license', 'unknown'), ('revision', 'main')])
def test_source_license_and_revision_must_be_locked(packet, field, value):
    packet[1]['providers'][0][field] = value
    with pytest.raises(ValueError):
        audit(packet)


def test_duplicate_observation_not_counted_as_new(packet):
    region = copy.deepcopy(packet[1]['regions'][0])
    region['id'] = 'different-name-same-person-frame'
    packet[1]['regions'].append(region)
    with pytest.raises(ValueError, match='Duplicate observation'):
        audit(packet)


def test_unknown_context_cannot_be_exported_as_background(packet):
    region = packet[1]['regions'][0]
    source = next(s for s in packet[1]['sources'] if s['id'] == region['source_id'])
    source['uncertain_boxes'] = [{'xyxy': region['roi']}]
    with pytest.raises(ValueError, match='Uncertain context'):
        validate_region(region, source)


def test_keeper_cannot_be_silently_merged_into_player(packet):
    region = next(r for r in packet[1]['regions'] if r['primary_role'] == 'goalkeeper')
    next(o for o in region['objects'] if o['id'] == region['primary_id'])['role'] = 'player'
    with pytest.raises(ValueError, match='Primary role'):
        audit(packet)


@pytest.mark.parametrize('change', ['unreviewed', 'extent', 'narrow', 'out_of_bounds'])
def test_unreviewed_or_changed_roi_rejected(packet, change):
    region = packet[1]['regions'][0]
    if change == 'unreviewed':
        region['review_status'] = 'pending'
    elif change == 'extent':
        region['roi'][0] += 1
    elif change == 'narrow':
        region['context_margin_px'] = 2
    else:
        region['objects'][0]['xyxy'][0] = -1
    with pytest.raises(ValueError):
        audit(packet)


def test_cannot_export_without_asset_verification(packet):
    with pytest.raises(ValueError, match='unverified assets'):
        audit(packet, export=packet[0] / 'export')
    assert not (packet[0] / 'export').exists()


def test_git_blob_hash_includes_object_header():
    assert git_blob_sha(b'hello\n') == 'ce013625030ba8dba906f756967f9e9ca394464a'


def test_near_duplicate_requires_both_visual_checks():
    feature = {'dhash': 0, 'thumbnail': np.zeros((36, 64), dtype=np.uint8)}
    references = [
        {'image': 'exact', 'dhash': 0, 'thumbnail': feature['thumbnail']},
        {'image': 'near', 'dhash': 15, 'thumbnail': feature['thumbnail'] + 3},
        {'image': 'different-layout', 'dhash': 31, 'thumbnail': feature['thumbnail']},
        {'image': 'different-intensity', 'dhash': 0, 'thumbnail': feature['thumbnail'] + 4},
    ]
    assert duplicate_hits(feature, references) == ['exact', 'near']
