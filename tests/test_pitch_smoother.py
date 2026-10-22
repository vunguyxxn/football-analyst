import math
import numpy as np
import pytest
from backend.common.schemas import TrackingRow
from backend.cv.pitch_smoother import PitchSmoother
from backend.cv.pitch_metrics import PitchMetrics


def row(i,x,y=34,track=1):
    return TrackingRow(frame=i,time_s=i/60,track_id=track,team='A',x_m=x,y_m=y)


def test_known_velocity_has_bounded_position_lag_and_correct_speed():
    smoother=PitchSmoother();metrics=PitchMetrics(60);accepted=[]
    for i in range(121):
        r,broken,_=smoother.observe(0,row(i,10+2*i/60))
        if broken:metrics.break_chain(0,1)
        if r:
            assert 0 <= 10+2*i/60-r.x_m < .3
            accepted.append(r);metrics.observe(0,r)
    state=metrics.report()['tracks'][0]
    assert state['max_speed_kmh']==pytest.approx(7.2,abs=.001)
    assert abs(state['distance_m']-state['duration_s']*2)<.15
    assert len(accepted)==116  # five warm-up frames, then current-time estimates


def test_stationary_noise_is_reduced_without_future_samples():
    smoother=PitchSmoother();rng=np.random.default_rng(42);raw=[];filtered=[]
    for i in range(180):
        x,y=np.array([40.,34.])+rng.uniform(-.1,.1,2)
        result,_,_=smoother.observe(0,row(i,x,y))
        if result and i>=30:
            raw.append(math.hypot(x-40,y-34));filtered.append(math.hypot(result.x_m-40,result.y_m-34))
    assert np.mean(np.square(filtered)) < .5*np.mean(np.square(raw))


def test_isolated_teleport_is_not_smoothed_into_a_plausible_run():
    smoother=PitchSmoother();metrics=PitchMetrics(60)
    for i in range(91):
        r,broken,status=smoother.observe(0,row(i,70 if i==35 else 10+i/60))
        if i==35:
            assert r is None and broken and status=='jump_rejected'
        if broken:metrics.break_chain(0,1)
        if r:
            assert r.x_m<12
            metrics.observe(0,r)
    assert metrics.report()['tracks'][0]['distance_m']<2


def test_persistent_relocation_starts_new_chain_not_a_teleport_distance():
    smoother=PitchSmoother();metrics=PitchMetrics(60);new=[]
    for i in range(120):
        r,broken,status=smoother.observe(0,row(i,10 if i<40 else 80))
        if broken:metrics.break_chain(0,1)
        if r:
            metrics.observe(0,r)
            if i>=40:new.append(r)
    assert new and new[0].x_m==pytest.approx(80)
    assert metrics.report()['tracks'][0]['distance_m']==pytest.approx(0)


def test_gap_and_calibration_boundary_reset_history_and_metrics():
    smoother=PitchSmoother();metrics=PitchMetrics(60)
    for i in list(range(31))+list(range(60,91)):
        r,broken,_=smoother.observe(0,row(i,10 if i<60 else 80))
        if broken:metrics.break_chain(0,1)
        if r:metrics.observe(0,r)
    assert metrics.report()['tracks'][0]['distance_m']==0
    assert smoother.observe(1,row(91,30))[0] is None
    smoother.advance(4)
    assert not smoother.tracks


def test_stop_response_has_bounded_overshoot_and_settles():
    smoother=PitchSmoother();errors=[];end=[]
    for i in range(121):
        truth=10+2*min(i/60,1)
        r,_,_=smoother.observe(0,row(i,truth))
        if r:
            errors.append(abs(r.x_m-truth))
            if i>=75:end.append(abs(r.x_m-truth))
    assert max(errors)<.3
    assert max(end)<.02


def test_timestamp_order_and_independent_tracks():
    smoother=PitchSmoother()
    for i in range(20):
        a,_,_=smoother.observe(0,row(i,10,track=1))
        b,_,_=smoother.observe(0,row(i,80,track=2))
    assert a.x_m==pytest.approx(10) and b.x_m==pytest.approx(80)
    with pytest.raises(ValueError,match='increase'):
        smoother.observe(0,row(19,10))


def test_filter_does_not_artificially_cap_velocity_at_40():
    smoother=PitchSmoother();observed=[]
    for i in range(121):
        r,_,_=smoother.observe(0,row(i,10+14*i/60))
        if r:observed.append(r)
    a,b=observed[-2:]
    assert (b.x_m-a.x_m)/(b.time_s-a.time_s)*3.6>40
