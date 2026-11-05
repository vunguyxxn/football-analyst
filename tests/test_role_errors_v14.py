import copy
import json
from pathlib import Path

import pytest

from backend.cv.audit_role_errors_v14 import replay, validate_review
from backend.cv.compare_role_models import frame_confusion, operating_metrics

ROOT = Path(__file__).resolve().parents[1]


def frame():
    labels=[{'id':i,'role':role,'xyxy':[i*100,0,i*100+20,50]} for i,role in enumerate(['player','goalkeeper','referee'])]
    return {'split':'val','image':'images/val/a.png','labels':labels,'predictions':{'v11':copy.deepcopy(labels),'v14':copy.deepcopy(labels)}}


def expected(f):
    return {v:{**operating_metrics(*frame_confusion(f['labels'],f['predictions'][v])),'frames':1} for v in ['v11','v14']}


def packet():
    review=json.loads((ROOT/'docs/fixtures/role_error_audit_review_v14.json').read_text())
    audit={k:review[k] for k in ['manifest_sha256','weights','size','confidence','nms_iou','matching_iou','max_det']}
    for original,key in [('keeper_fp_rows','keeper_predictions'),('old_keeper_fp_rows','old_keeper_predictions'),('all_referee_rows','referee_labels')]:
        # Preserve one score-bearing original field to exercise immutable evidence checks.
        audit[original]=[{k:copy.deepcopy(r[k]) for k in ['review_id','image','xyxy','transition']+(['prediction'] if key!='referee_labels' else ['v11','v14','label_id'])} for r in review[key]]
    return audit,review


def test_replay_reproduces_all_three_classes_and_rejects_changed_counts():
    f=frame();e=expected(f)
    assert replay([f],e)==e
    f['predictions']['v14'][0]['role']='goalkeeper'
    with pytest.raises(ValueError,match='All-class validation'):
        replay([f],e)


def test_replay_rejects_test_heldout_and_duplicate_frames():
    f=frame();e=expected(f)
    for change in [{'split':'test'},{'match_id':'128057'}]:
        with pytest.raises(ValueError,match='unique validation'):
            replay([{**f,**change}],e)
    with pytest.raises(ValueError,match='unique validation'):
        replay([f,f],e)


def test_review_covers_old_and_current_fp_and_every_referee_gt():
    a,r=packet()
    assert validate_review(a,r)=={'keeper_predictions':110,'old_keeper_predictions':49,'referee_labels':292}
    for key in ['keeper_predictions','old_keeper_predictions','referee_labels']:
        a,r=packet();r[key].pop()
        with pytest.raises(ValueError,match='coverage'):
            validate_review(a,r)


def test_review_cannot_change_boxes_scores_or_transition():
    for key,field,value in [('keeper_predictions','xyxy',[0,0,1,1]),('old_keeper_predictions','transition','new_fp'),('referee_labels','label_id',999)]:
        a,r=packet();r[key][0][field]=value
        with pytest.raises(ValueError,match='Frozen audit evidence'):
            validate_review(a,r)
    a,r=packet();r['keeper_predictions'][0]['prediction']['confidence']=1.0
    with pytest.raises(ValueError,match='Frozen audit evidence'):
        validate_review(a,r)


def test_review_cannot_claim_test_inference_or_change_thresholds():
    for field,value in [('confidence',.1),('half',True),('cross_role_dedup',True),('independently_validated',True),('test_inference_performed',True)]:
        a,r=packet();r[field]=value
        with pytest.raises(ValueError):validate_review(a,r)


def test_visual_subjects_and_attributes_must_be_explicit():
    a,r=packet();r['referee_labels'][0]['location']='top_of_image'
    with pytest.raises(ValueError,match='visual attributes'):validate_review(a,r)
    a,r=packet();r['keeper_predictions'][0]['visual_subject']=''
    with pytest.raises(ValueError,match='visual subject'):validate_review(a,r)
