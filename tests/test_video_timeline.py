import copy

import pytest

from backend.tactics.video_timeline import build_timeline, compare
from backend.tactics.video_tactics import build_report


def example():
    windows = [{"segment": i, "group": "A", "start_s": i*10., "end_s": (i+1)*10.,
                "status": "observed_cluster", "support": {"seconds": 10.}, "snapshot": {"time_s": i*10.+5},
                "review": {"attack_direction": 1}} for i in (0,1)]
    frames = {}
    for f in range(200):
        later = f >= 100
        frames[f] = [{"frame":f,"time_s":f/10,"track_id":i,"team":"A",
                      "x_m":x+(6 if later else 0), "y_m":y+(6 if later and y==20 else 0)}
                     for i,(x,y) in enumerate(((10.,10.),(10.,20.),(30.,10.),(30.,20.)))]
    return windows,frames


def test_same_cohort_metrics_ignore_other_people_and_keep_traceable_evidence():
    windows,frames=example()
    for f,people in frames.items():
        people.append({"frame":f,"time_s":f/10,"track_id":50 if f<100 else 60,"team":"A","x_m":90.,"y_m":60.})
    original=copy.deepcopy(frames)
    result=compare(*windows,frames,10)
    assert result['status']=='observed_cohort_comparison'
    assert result['cohort_ids']==[0,1,2,3]
    assert result['before']['metrics']['width_m']==10
    assert result['after']['metrics']['width_m']==16
    assert result['deltas']['width_m']==6
    assert result['deltas']['nearest_m']==6
    assert result['deltas']['forward_m']==6
    assert result['before']['evidence_time_s']==5
    assert result['after']['evidence_time_s']==15
    for observation in result['observations']:
        assert observation['delta']==result['deltas'][observation['metric']]
        assert observation['coach_check']
    assert frames==original


def test_identical_positions_with_new_ids_are_not_a_common_team_cohort():
    windows,frames=example()
    for f,people in frames.items():
        if f>=100:
            for row in people: row['track_id']+=10
    result=compare(*windows,frames,10)
    assert result['status']=='insufficient_common_ids'
    assert result['deltas'] is None and result['observations']==[]


def test_individual_stability_does_not_replace_simultaneous_visibility():
    windows,frames=example()
    for f in range(80):
        missing=f//20
        frames[f]=[r for r in frames[f] if r['track_id']!=missing]
        frames[f].append({"frame":f,"time_s":f/10,"track_id":1000+f,"team":"A","x_m":80.,"y_m":30.})
    result=compare(*windows,frames,10)
    assert result['cohort_ids']==[0,1,2,3]
    assert result['status']=='insufficient_joint_visibility'
    assert result['before']['support']['seconds']==2
    assert result['before']['metrics'] is None and result['deltas'] is None


def test_missing_windows_and_gaps_are_never_bridged():
    windows,frames=example()
    middle=copy.deepcopy(windows[1]);middle.update(status='insufficient_data',snapshot=None)
    third=copy.deepcopy(windows[1]);third.update(segment=2,start_s=20.,end_s=30.)
    timeline=build_timeline([windows[0],middle,third],frames,10)
    pairs=timeline['groups'][0]['comparisons']
    assert len(pairs)==2 and all(p['status']=='insufficient_windows' for p in pairs)
    assert [(p['from_segment'],p['to_segment']) for p in pairs]==[(0,1),(1,2)]
    assert compare(windows[0],third,frames,10)['status']=='gap_between_windows'
    assert timeline['groups'][1]['entries']==[]


@pytest.mark.parametrize('directions',[(None,None),(1,-1),(-1,-1)])
def test_forward_shift_requires_same_known_direction(directions):
    windows,frames=example()
    for window,direction in zip(windows,directions): window['review']={'attack_direction':direction}
    result=compare(*windows,frames,10)
    assert result['deltas']['center_x_m']==6
    if directions==(-1,-1):
        assert result['deltas']['forward_m']==-6
        observation=next(o for o in result['observations'] if o['metric']=='forward_m')
        assert observation['after']-observation['before']==observation['delta']
    else:
        assert result['deltas']['forward_m'] is None
        assert all(o['metric']!='forward_m' for o in result['observations'])


def test_zero_change_does_not_produce_a_claim_of_optimal_or_unchanged_tactics():
    windows,frames=example()
    for f in range(100,200):
        frames[f]=[{**row,'frame':f,'time_s':f/10} for row in frames[f-100]]
    result=compare(*windows,frames,10)
    assert all(value==0 for value in result['deltas'].values())
    assert result['observations']==[]
    assert result['status']=='observed_cohort_comparison'


def test_report_wires_timeline_to_validated_positions_and_keeps_missing_groups_null():
    windows,frames=example()
    rows=[row for people in frames.values() for row in people]
    calibration={'source_sha256':'source','person_job_id':'job','segments':[
        {key:window[key] for key in ('segment','start_s','end_s')} for window in windows]}
    report=build_report(rows,calibration,10,200)
    a,b=report['timeline']['groups']
    assert a['comparisons'][0]['status']=='observed_cohort_comparison'
    assert a['comparisons'][0]['deltas']['width_m']==6
    assert b['comparisons'][0]['deltas'] is None
    assert all(entry['status']=='insufficient_data' for entry in b['entries'])
