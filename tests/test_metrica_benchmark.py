import csv
import hashlib
import json
import math

import numpy as np
import pytest

from backend.common.schemas import TrackingRow
from backend.cv.metrica_benchmark import (
    AuditedMetrics, Trajectory, corrupt, evaluate_trajectory, load_tracking, run, summarize,
)


def config():
    return {"start_s": 0, "stop_s": 60, "period": 1, "noise_sigma_m": .15,
            "spike_probability": .1, "gap_duration_s": .6, "relocation_duration_s": .6,
            "lag_grid_frames": list(range(7)), "seeds": [1729], "scenarios": ["clean", "noise"]}


def trajectory(seconds=60, velocity=0):
    times = np.arange(round(seconds*25)) / 25
    return Trajectory(1, 7, "A", np.arange(len(times)), times,
                      np.c_[20+velocity*times, np.full(len(times), 30.)],
                      np.zeros(len(times), dtype=int), 25)


def csv_file(tmp_path):
    path = tmp_path / 'tracking.csv'
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['','','','Home','',''])
        writer.writerow(['','','','7','',''])
        writer.writerow(['Period','Frame','Time [s]','Player7','','Ball',''])
        for frame, x in enumerate([.25, .25, 'NaN', 1.1, .25, .25], 1):
            writer.writerow([1,frame,frame/25,x,.2,.5,.5])
    return path


def test_loader_converts_axes_omits_ball_and_splits_native_missing(tmp_path):
    source = csv_file(tmp_path)
    series, info = load_tracking(source, 1, 'B', 0, 1)
    assert len(series) == 1
    t = series[0]
    assert t.track_id == 1007 and t.team == 'B' and t.fps == 25
    assert t.frames.tolist() == [1,2,5,6]
    np.testing.assert_allclose(t.xy, [[26.25,54.4]]*4)
    assert t.segments.tolist() == [0,0,1,1]
    assert info['missing'] == info['outside'] == 1


def test_faults_are_reproducible_and_do_not_mutate_reference():
    t = trajectory()
    original = t.xy.copy()
    for scenario in ('clean','noise','spikes','gaps','relocation'):
        a = corrupt(t, scenario, 42, config())
        b = corrupt(t, scenario, 42, config())
        for x,y in zip(a[:3],b[:3]):
            np.testing.assert_array_equal(x,y)
    np.testing.assert_array_equal(t.xy,original)
    a = corrupt(t,'noise',42,config())[0]
    b = corrupt(t,'noise',43,config())[0]
    assert not np.array_equal(a,b)


def test_long_fault_and_missing_bursts_are_not_just_single_spikes():
    t = trajectory()
    _, keep, _, detail = corrupt(t,'gaps',42,config())
    assert detail['injected_missing'] == 45
    assert not keep[750:765].any()
    observed, _, fault, _ = corrupt(t,'relocation',42,config())
    assert fault.sum() == 15
    assert np.linalg.norm((observed-t.xy)[fault],axis=1).min() > 12


def test_metric_audit_uses_reference_curve_not_only_endpoint_chord():
    t = Trajectory(1,7,'A',np.arange(3),np.array([0.,.25,.5]),
                   np.array([[10.,10.],[11.,11.],[12.,10.]]),np.zeros(3,dtype=int),4)
    metrics = AuditedMetrics(t)
    for frame,time,xy in zip(t.frames,t.times,t.xy):
        metrics.observe(0,TrackingRow(frame=int(frame),time_s=time,track_id=7,team='A',x_m=xy[0],y_m=xy[1]))
    result=metrics.totals()
    assert result['distance_m']==pytest.approx(2)
    assert result['reference_covered_distance_m']==pytest.approx(2*math.sqrt(2))
    assert result['speed_error_time']==pytest.approx((2*math.sqrt(2)-2)*3.6)


def test_clean_constant_velocity_reference_has_no_injected_position_error():
    t = trajectory(seconds=4,velocity=2)
    result = evaluate_trajectory(t,'clean',1729,config())
    s = summarize([result],25,config()['lag_grid_frames'])
    assert s['raw_position_rmse_m']==0
    assert s['filtered_position_rmse_m'] < 1e-10
    assert s['filtered_coverage'] < 1
    assert s['apparent_lag_ms'] == 0
    assert abs(s['filtered_motion']['covered_distance_relative_error']) < .1
    assert s['filtered_motion']['represented_time_fraction'] < 1


def test_corrupt_positions_are_compared_at_same_accepted_frames():
    t = trajectory(seconds=4)
    result = evaluate_trajectory(t,'spikes',1729,config())
    s = summarize([result],25,config()['lag_grid_frames'])
    assert s['raw_position_rmse_m'] > s['filtered_position_rmse_m']
    assert result['filtered_count'] < result['raw_count']
    assert result['common_raw_squared_error'] <= result['raw_squared_error']
    assert s['raw_motion']['full_distance_relative_error'] is None  # zero-distance reference


def test_source_hash_and_existing_report_are_guarded(tmp_path):
    source=csv_file(tmp_path)
    manifest=tmp_path/'manifest.json'
    spec={'source':'test','repository':'test','commit':'test','benchmark':config(),
          'files':[{'filename':source.name,'sha256':'wrong','game':1,'team':'Home'}]}
    manifest.write_text(json.dumps(spec))
    output=tmp_path/'report.json'
    with pytest.raises(ValueError,match='hash'):
        run(tmp_path,manifest,output)
    assert not output.exists()
    spec['files'][0]['sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(spec))
    report=run(tmp_path,manifest,output)
    assert len(report['trials'])==2
    json.loads(output.read_text())
    with pytest.raises(ValueError,match='new file'):
        run(tmp_path,manifest,output)
