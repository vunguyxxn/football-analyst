import copy
import json
from collections import Counter
from pathlib import Path
import pytest

from backend.cv.prepare_role_merge_v14 import allocate, label_counts, validate_sampling
from backend.cv.evaluate_role_detector import digest

ROOT = Path(__file__).resolve().parents[1]


def test_shared_parent_has_one_budget_including_negative():
    rows = [{'split':'train','parent':'a','negative':False},
            {'split':'train','parent':'a','negative':True},
            {'split':'train','parent':'b','negative':False}]
    result = allocate(rows)
    assert [n for r,n in result] == [1,1,1]
    with pytest.raises(ValueError, match='train only'):
        allocate([{'split':'val','parent':'a'}])
    with pytest.raises(ValueError, match='ROI cap'):
        allocate(rows[:2]+[rows[0]])


def test_protocol_keeps_training_and_evaluation_and_v11_bytes_locked():
    old = json.loads((ROOT/'docs/fixtures/role_sources_training_protocol_v11.json').read_text())
    new = json.loads((ROOT/'docs/fixtures/role_sources_training_protocol_v14.json').read_text())
    for key in ['models','epochs','image_size','batch','amp','optimizer','lr0','seed','workers','mosaic',
                'close_mosaic','multi_scale','evaluation_lock','validation_gate','comparison_baseline']:
        assert new[key] == old[key]
    ledger = json.loads((ROOT/new['parent_sampling']).read_text())
    assert digest(ROOT/new['parent_sampling']) == new['parent_sampling_sha256']
    assert len(ledger['exposures']) == 418
    assert sum(ledger['parent_exposures'].values()) == 418
    added = ledger['exposures'][409:]
    assert sorted(Counter(r['sampling_parent'] for r in added).values()) == [1]*7+[2]
    assert sum('goal-background' in r['image'] for r in added) == 1
    assert sum('29-field' in r['image'] for r in added) == 1
    assert set(new['comparison_references']) == {'v6','v11'}


def sampling_fixture():
    p = json.loads((ROOT/'docs/fixtures/role_sources_training_protocol_v14.json').read_text())
    ledger = json.loads((ROOT/p['parent_sampling']).read_text())
    rows = [{**r,'split':'train','source':r['family'],'pixel_sha256':r['image_sha256']} for r in ledger['exposures']]
    rows += [{'split':split,'sampling_parent':split+str(i),'family':split,'source':split,'pixel_sha256':split+str(i)}
             for split,count in [('val',128),('test',35)] for i in range(count)]
    m = {'files':rows, 'images':p['expected_images']}
    return p, m


def test_sampling_rejects_missing_duplicated_or_reparented_exposure():
    p, m = sampling_fixture()
    validate_sampling(ROOT, p, m)
    for mutation in ['missing','duplicate','parent','label']:
        bad = copy.deepcopy(m)
        if mutation == 'missing':bad['files'].pop(0)
        if mutation == 'duplicate':bad['files'].append(bad['files'][0])
        if mutation == 'parent':bad['files'][0]['sampling_parent'] = 'wrong'
        if mutation == 'label':bad['files'][0]['label_sha256'] = 'wrong'
        with pytest.raises(ValueError, match='sampling changed'):
            validate_sampling(ROOT, p, bad)


def test_sampling_rejects_parent_leakage_and_heldout_match():
    p, m = sampling_fixture()
    m['files'][418]['sampling_parent'] = m['files'][0]['sampling_parent']
    with pytest.raises(ValueError, match='Parent crosses split'):
        validate_sampling(ROOT, p, m)
    p, m = sampling_fixture()
    m['files'][0]['match_id'] = '128057'
    with pytest.raises(ValueError, match='Heldout match'):
        validate_sampling(ROOT, p, m)


def test_strict_labels_and_empty_negative(tmp_path):
    path = tmp_path/'labels.txt'
    path.write_text('')
    assert label_counts(path) == {}
    path.write_text('0 0.5 0.5 0.1 0.2\n1 0.5 0.5 0.1 0.2\n2 0.5 0.5 0.1 0.2\n')
    assert label_counts(path) == {'player':1,'goalkeeper':1,'referee':1}
    for bad in ['3 0.5 0.5 0.1 0.2','0 nan 0.5 0.1 0.2','0 0.1 0.5 0.4 0.2','0 0.5 0.5 0 0.2']:
        path.write_text(bad)
        with pytest.raises(ValueError):
            label_counts(path)


def test_no_two_positive_rois_can_silently_expand_a_parent_budget():
    with pytest.raises(ValueError, match='ROI cap'):
        allocate([{'split':'train','parent':'a','negative':False}]*2)
