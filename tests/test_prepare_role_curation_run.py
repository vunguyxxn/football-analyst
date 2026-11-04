import json
from pathlib import Path

import pytest

from backend.cv.evaluate_role_detector import digest
from backend.cv.prepare_role_curation_run import prepare
from backend.cv.prepare_role_dataset import NAMES, yaml_text


def fixture(root):
    source=root/'curated'
    source.mkdir()
    cp=root/'curation.json'
    cp.write_text('{}')
    rows=[]
    for split in ['train','val','test']:
        row={'split':split,'family':split,'source':split,'pixel_sha256':split}
        for kind,folder,ext in [('image','images','png'),('label','labels','txt')]:
            rel=f'{folder}/{split}/a.{ext}'
            path=source/rel
            path.parent.mkdir(parents=True)
            path.write_bytes((split if kind=='image' else '0 .5 .5 .1 .2\n').encode())
            row[kind]=rel;row[kind+'_sha256']=digest(path)
        rows.append(row)
    m={'names':NAMES,'protocol_sha256':digest(cp),'files':rows,'images':{s:1 for s in ['train','val','test']}}
    (source/'manifest.json').write_text(json.dumps(m))
    (source/'data.yaml').write_text(yaml_text(source))
    pp=root/'train.json'
    pp.write_text(json.dumps({'curated_dataset':'curated','curated_manifest_sha256':digest(source/'manifest.json'),
         'curation_protocol':'curation.json','curation_protocol_sha256':digest(cp),'dataset':'training/dataset',
         'expected_images':m['images'],'plan':'plan.json'}))
    return source,pp


def test_training_snapshot_preserves_every_image_label_record_and_curated_manifest(tmp_path):
    source,pp=fixture(tmp_path)
    original=(source/'manifest.json').read_bytes()
    plan=prepare(tmp_path,pp)
    assert plan['all_image_label_records_unchanged'] is True
    assert (source/'manifest.json').read_bytes()==original
    bound=json.loads((tmp_path/'training/dataset/manifest.json').read_text())
    assert bound['protocol_sha256']==digest(pp)
    assert bound['files']==json.loads(original)['files']
    with pytest.raises(ValueError,match='new workspace'):
        prepare(tmp_path,pp)


def test_source_tamper_and_wrong_image_count_block_snapshot(tmp_path):
    source,pp=fixture(tmp_path)
    p=json.loads(pp.read_text())
    p['expected_images']['train']=2
    pp.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='count'):
        prepare(tmp_path,pp)
    assert not (tmp_path/'training').exists()
    (source/'labels/val/a.txt').write_text('2 .5 .5 .1 .2\n')
    with pytest.raises(ValueError):
        prepare(tmp_path,pp)
    assert not (tmp_path/'training').exists()


def test_v11_training_settings_match_v10_and_only_fresh_coco_small_is_locked():
    root=Path(__file__).resolve().parents[1]
    fixtures=root/'docs/fixtures'
    p=json.loads((fixtures/'role_sources_training_protocol_v11.json').read_text())
    old=json.loads((fixtures/'role_sources_training_protocol_v10.json').read_text())
    for key in ['models','epochs','image_size','batch','amp','optimizer','lr0','seed','mosaic','close_mosaic',
                'multi_scale','evaluation_lock','validation_gate','test_confidence','test_nms_iou','max_detections']:
        assert p[key]==old[key]
    assert [s['id'] for s in p['models']]==['small']
    assert p['models'][0]['sha256']=='85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5'
