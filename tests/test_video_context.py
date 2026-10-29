import copy
import json

import numpy as np
import pytest

from backend.tactics.partial_formation import fit_snapshot
from backend.tactics.formation_templates import template_points
from backend.tactics.video_context import prepare, load_context, digest, validate_context, window_context, role_for
from backend.tactics.video_tactics import build_report


def context():
    return {"kind":"video_context_development_review_v1","independently_validated":False,
            "fps":10,"team_labels":{"A":"Áo đỏ","B":"Áo trắng"},
            "role_tracks":[{"id":99,"role":"referee","start_frame":0,"end_frame":100,"review_frames":[0,99]}],
            "directions":[{"start_s":0,"end_s":10,"A":1,"B":-1}],
            "window_notes":[{"start_s":0,"end_s":10,"frames":[20,50,80],"note":"Chưa chốt sơ đồ"}],"audit":{}}


def test_review_excludes_only_scoped_roles_before_metrics_without_changing_source():
    ctx=context()
    rows=[{"frame":frame,"time_s":frame/10,"team":"A","track_id":i,"x_m":float(x),"y_m":float(y)}
          for frame in range(100) for i,(x,y) in enumerate(template_points("4-4-2")[:8]*[20,20]+[52.5,34])]
    rows += [{"frame":frame,"time_s":frame/10,"team":"A","track_id":99,"x_m":100.,"y_m":60.} for frame in range(100)]
    original=copy.deepcopy(rows)
    calibration={"person_job_id":"job","source_sha256":"source","segments":[{"segment":0,"start_s":0.,"end_s":10.}]}
    raw=build_report(rows,calibration,10,100)
    clean=build_report(rows,calibration,10,100,ctx)
    assert raw['windows'][0]['metrics']['median_people']==9
    assert clean['windows'][0]['metrics']['median_people']==8
    assert clean['windows'][0]['metrics']['median_depth_m']==20
    assert np.sum(clean['windows'][0]['heatmap_seconds'])==pytest.approx(80)
    assert clean['context_review']['removed_team_observations']==100
    assert clean['windows'][0]['review']['attack_direction']==1
    assert all(c['attack_direction_hypothesis']==1 for c in clean['windows'][0]['formation']['candidates'])
    assert rows==original
    rule=ctx['role_tracks'][0]
    rule.update(start_frame=20,end_frame=40,review_frames=[20,39])
    assert role_for({'frame':19,'track_id':99},ctx) is None
    assert role_for({'frame':20,'track_id':99},ctx)=='referee'
    assert role_for({'frame':40,'track_id':99},ctx) is None
    assert role_for({'frame':20,'track_id':1},ctx) is None
    assert window_context(ctx,{'start_s':9,'end_s':11},'A')['attack_direction'] is None


def test_direction_constraint_never_mirrors_known_orientation_to_improve_score():
    people=[{'track_id':i,'x_m':float(x),'y_m':float(y)} for i,(x,y) in enumerate(template_points('4-2-3-1')*[20,20]+[52.5,34])]
    good=fit_snapshot(people,1); wrong=fit_snapshot(people,-1)
    assert all(item['attack_direction_hypothesis']==1 for item in good)
    assert all(item['attack_direction_hypothesis']==-1 for item in wrong)
    a=next(item for item in good if item['shape']=='4-2-3-1')
    b=next(item for item in wrong if item['shape']=='4-2-3-1')
    assert a['rmse_m']<1e-6 and b['rmse_m']>1
    for invalid in (0,True,2):
        with pytest.raises(ValueError): fit_snapshot(people,invalid)


def setup_review(tmp_path):
    job=tmp_path/'job';job.mkdir()
    (job/'source.mp4').write_bytes(b'video context fixture')
    result={'fps':1,'frames':10,'chunks':1,'source_sha256':digest(job/'source.mp4')}
    (job/'status.json').write_text(json.dumps({'status':'completed','result':result}))
    records=[{'frame':f,'boxes':[{'id':1,'group':'A','xyxy':[1,1,2,3]},{'id':99,'group':'B','xyxy':[5,1,6,3]}]} for f in range(10)]
    (job/'chunk-0.json').write_text(json.dumps({'frames':records}))
    (job/'pitch_estimate').mkdir();(job/'pitch_estimate/tracking.jsonl').write_bytes(b'positions bound to review')
    review=context();review.pop('fps');review.pop('audit');review.update(person_job_id=job.name,source_sha256=result['source_sha256'],frames=[2,5,8])
    review['role_tracks'][0].update(end_frame=10,review_frames=[0,5,9])
    review['window_notes'][0]['frames']=[2,5,8]
    review['labels']=[{'frame':f,'id':b['id'],'xyxy':b['xyxy'],'role':'red_outfield' if b['id']==1 else 'referee'}
                      for f in review['frames'] for b in records[f]['boxes']]
    labels=tmp_path/'labels.json';labels.write_text(json.dumps(review))
    return job,result,review,labels


def test_prepare_audits_nonplayer_contamination_separately_from_outfield_accuracy(tmp_path):
    job,result,review,labels=setup_review(tmp_path)
    output=job/'tactical_context'
    report=prepare(job,labels,output)
    assert report['audit']['sampled_people']==6
    assert report['audit']['outfield_people']==report['audit']['correct_outfield_group']==3
    assert report['audit']['referee_in_team_groups']==report['audit']['referee_samples']==3
    assert report['audit']['goalkeeper_samples']==0
    assert load_context(job,result)==report
    assert report['independently_validated'] is False


@pytest.mark.parametrize('change',['label_duplicate','label_missing','wrong_box','conflicting_role','foreign_source','reserved_fields'])
def test_prepare_refuses_invalid_review_before_writing(tmp_path,change):
    job,_,review,labels=setup_review(tmp_path)
    if change=='label_duplicate': review['labels'].append(review['labels'][0])
    if change=='label_missing': review['labels'].pop()
    if change=='wrong_box': review['labels'][0]['xyxy']=[0,0,1,1]
    if change=='conflicting_role': review['labels'][1]['role']='white_outfield'
    if change=='foreign_source': review['source_sha256']='other'
    if change=='reserved_fields': review['audit']={'accuracy':1.0}
    labels.write_text(json.dumps(review))
    with pytest.raises(ValueError): prepare(job,labels,job/'tactical_context')
    assert not (job/'tactical_context').exists()


@pytest.mark.parametrize('change',['labels','positions','chunks','source','payload'])
def test_runtime_rejects_stale_context_and_absent_context_never_assumes_teams(tmp_path,change):
    job,result,_,labels=setup_review(tmp_path)
    assert load_context(job,result) is None
    prepare(job,labels,job/'tactical_context')
    if change=='labels': labels.write_text(labels.read_text()+' ')
    if change=='positions': (job/'pitch_estimate/tracking.jsonl').write_bytes(b'reprojected')
    if change=='chunks': (job/'chunk-0.json').write_text('{}')
    if change=='source': result['source_sha256']='other'
    if change=='payload':
        path=job/'tactical_context/report.json';payload=json.loads(path.read_text());payload['directions'][0]['A']=-1;path.write_text(json.dumps(payload))
    with pytest.raises(ValueError): load_context(job,result)


def test_context_rejects_outside_role_evidence_and_invalid_direction():
    ctx=context();ctx['role_tracks'][0]['review_frames']=[0,100]
    with pytest.raises(ValueError): validate_context(ctx,10,100)
    ctx=context();ctx['directions'][0]['A']=True
    with pytest.raises(ValueError): validate_context(ctx,10,100)
