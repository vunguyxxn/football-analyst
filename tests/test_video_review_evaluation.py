import json
import math
import random

import pytest

from backend.cv.evaluate_video_review import (
    assign_points, canonical_hash, evaluate_frame, run, summarize,
)


def label(identity='A01', xy=(0,0), visibility='visible'):
    return {'identity':identity,'team':'A','xy':list(xy),'visibility':visibility}


def prediction(track_id=1, xy=(0,0), team='A'):
    return {'track_id':track_id,'team':team,'image_xy':list(xy)}


def test_assignment_revises_a_greedy_choice_to_keep_both_people():
    result=assign_points([(0,0),(3,0)],[(1,0),(-2,0)],2.1)
    assert {(i,j) for i,j,_ in result}=={(0,1),(1,0)}
    assert sum(d for _,_,d in result)==pytest.approx(4)


def test_assignment_agrees_with_exhaustive_optimum_on_small_point_sets():
    rng=random.Random(42)
    for _ in range(30):
        refs=[(rng.random()*10,rng.random()*10) for _ in range(rng.randrange(5))]
        preds=[(rng.random()*10,rng.random()*10) for _ in range(rng.randrange(5))]
        gate=rng.uniform(1,8)
        def brute(i,used,n,cost):
            if i==len(refs):return (-n,cost)
            choices=[brute(i+1,used,n,cost)]
            for j,p in enumerate(preds):
                distance=math.dist(refs[i],p)
                if j not in used and distance<=gate:
                    choices.append(brute(i+1,used|{j},n+1,cost+distance))
            return min(choices)
        count,cost=brute(0,set(),0,0.)
        result=assign_points(refs,preds,gate)
        assert len(result)==-count
        assert sum(d for _,_,d in result)==pytest.approx(cost,abs=1e-10)
        assert len({i for i,_,_ in result})==len({j for _,j,_ in result})==len(result)


def test_uncertain_labels_are_excluded_and_matching_does_not_use_team():
    labels=[label(),label('A02',(20,0),'uncertain')]
    result=evaluate_frame(labels,[prediction(7,team='B'),prediction(8,(20,0)),prediction(9,(100,0))],5)
    assert result['visible_labels']==1 and result['excluded_labels']==1
    assert result['matches'][0]['predicted_team']=='B'
    assert result['predictions_near_excluded_labels']==[8]
    assert result['unmatched_prediction_ids']==[9]
    ambiguous=evaluate_frame([label(),label('A02',(1,0),'occluded')],[prediction()],5)
    assert ambiguous['matches'][0]['ambiguous']


def test_sparse_identity_changes_do_not_bridge_ambiguous_or_missing_samples():
    def frame(i,rows):
        return {'frame':i,'clip':'test',**evaluate_frame([label()],rows,2)}
    clear=[frame(0,[prediction(1)]),frame(1,[prediction(2)])]
    assert len(summarize(clear,90)['apparent_sampled_identity_changes'])==1
    ambiguous=[clear[0],frame(1,[prediction(2),prediction(3,(1,0))]),frame(2,[prediction(4)])]
    assert summarize(ambiguous,90)['sampled_identity_intervals']==0
    missing=[clear[0],frame(1,[]),frame(2,[prediction(4)])]
    assert summarize(missing,90)['apparent_sampled_identity_changes']==[]
    assert len(summarize(missing,90)['sample_match_disappearances'])==1
    assert summarize([clear[0],frame(100,[prediction(4)])],90)['sampled_identity_intervals']==0


def test_frozen_diagnostic_is_reproducible_and_not_independent_truth(tmp_path):
    output=tmp_path/'report.json'
    report=run('docs/fixtures/video_review_evaluation.json',output)
    assert report['independent_ground_truth'] is False and report['annotation_author_type']=='agent'
    primary=next(t for t in report['trials'] if t['gate_px']==12)
    assert primary['raw']['summary']['prediction_observations']==153
    assert primary['filtered']['summary']['prediction_observations']==140
    for stage in ('raw','filtered'):
        counts=[t[stage]['summary']['matched_observations'] for t in report['trials']]
        assert counts==sorted(counts)
        assert all(t[stage]['summary']['matched_observations']<=t[stage]['summary']['visible_label_observations']
                   for t in report['trials'])
    saved=json.loads(output.read_text(encoding='utf-8'))
    assert saved==report
    with pytest.raises(ValueError,match='new report'):
        run('docs/fixtures/video_review_evaluation.json',output)


@pytest.mark.parametrize('invalid',['hash','source','duplicate_id','pixel'])
def test_input_tampering_or_invalid_data_stops_before_report(tmp_path,invalid):
    from pathlib import Path
    spec=json.loads(Path('docs/fixtures/video_review_evaluation.json').read_text())
    kind='labels' if invalid=='pixel' else 'predictions'
    data=json.loads(Path(spec[kind]).read_text(encoding='utf-8'))
    if invalid=='source':data['source_sha256']='different'
    elif invalid=='duplicate_id':data['frames'][0]['raw'].append(data['frames'][0]['raw'][0])
    elif invalid=='pixel':data['frames']['1105']['A'][0][1]=99999
    else:data['scope']='changed'
    copied=tmp_path/'input.json';copied.write_text(json.dumps(data),encoding='utf-8')
    spec[kind]=str(copied)
    if invalid!='hash':spec[f'{kind}_canonical_sha256']=canonical_hash(data)
    protocol=tmp_path/'protocol.json';protocol.write_text(json.dumps(spec),encoding='utf-8')
    output=tmp_path/'failed.json'
    with pytest.raises(ValueError):run(protocol,output)
    assert not output.exists()
