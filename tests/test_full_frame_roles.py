import copy
import json
from pathlib import Path

import pytest

from backend.cv.export_full_frame_roles import labels


def source():
    return {'review_status':'agent_reviewed','uncertain_boxes':[], 'width':1280,'height':720,
            'objects':[{'id':'tiny','role':'player','xyxy':[10,20,20,40]},
                       {'id':'keeper','role':'goalkeeper','xyxy':[30,50,40,80]}]}


def test_native_full_frame_normalization_preserves_small_person_and_keeper():
    rows=[line.split() for line in labels(source()).splitlines()]
    assert rows[0][0]=='0'
    assert float(rows[0][4])==pytest.approx(20/720)
    assert rows[1][0]=='1'


@pytest.mark.parametrize('bad',['unreviewed','uncertain','duplicate','outside'])
def test_incomplete_or_corrupt_full_frame_cannot_be_exported(bad):
    s=source()
    if bad=='unreviewed':s['review_status']='pending'
    elif bad=='uncertain':s['uncertain_boxes']=[{'xyxy':[1,2,3,4]}]
    elif bad=='duplicate':s['objects'].append(copy.deepcopy(s['objects'][0]))
    else:s['objects'][0]['xyxy'][0]=-1
    with pytest.raises(ValueError):labels(s)


def test_packet_has_reviewed_full_images_and_all_three_roles():
    p=json.loads((Path(__file__).resolve().parents[1]/'docs/fixtures/full_frame_roles_v4.json').read_text())
    assert len(p['sources'])==3
    assert sum(len(labels(s).splitlines()) for s in p['sources'])==60
    assert {o['role'] for s in p['sources'] for o in s['objects']}=={'player','goalkeeper','referee'}
