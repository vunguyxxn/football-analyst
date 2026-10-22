import pytest
from backend.cv.team_smoother import TrackRoleSmoother


def test_warmup_and_single_color_error_do_not_flip_team():
    smoother = TrackRoleSmoother(60)
    assert [smoother.update(i, 1, 'A') for i in range(6)] == ['unknown']*5+['A']
    assert smoother.update(6, 1, 'referee') == 'unknown'
    assert smoother.update(7, 1, 'A') == 'A'


def test_conflict_and_unknown_are_not_forced_into_a_team():
    smoother = TrackRoleSmoother(60)
    for i in range(60):
        assert smoother.update(i, 1, ['A','B'][i%2]) == 'unknown'
        assert smoother.update(i, 2, 'unknown') == 'unknown'
    for i in range(60,90):
        result=smoother.update(i, 1, 'unknown')
    assert result=='unknown'


def test_sustained_new_evidence_can_correct_an_initial_wrong_label():
    smoother = TrackRoleSmoother(60)
    for i in range(30):
        smoother.update(i, 1, 'A')
    results=[smoother.update(i, 1, 'referee') for i in range(30,60)]
    assert results[0]=='unknown'
    assert 'unknown' in results
    assert results[-1]=='referee'  # no permanent lock to first team


def test_tracks_do_not_share_evidence_and_missing_track_expires():
    smoother=TrackRoleSmoother(60)
    for i in range(6):
        a=smoother.update(i, 7, 'A')
        b=smoother.update(i, 8, 'B')
    assert (a,b)==('A','B')
    smoother.advance(35)
    assert not smoother.histories
    assert smoother.update(35, 7, 'referee')=='unknown'
    for i in range(36,41):
        result=smoother.update(i,7,'referee')
    assert result=='referee'


def test_history_is_bounded_in_time_and_empty_frames_age_it():
    smoother=TrackRoleSmoother(60)
    for i in range(1000):
        smoother.update(i,1,'B')
        assert len(smoother.histories[1])<=30
    smoother.advance(1029)
    assert not smoother.histories


def test_duplicate_updates_and_backwards_time_are_rejected():
    smoother=TrackRoleSmoother(10)
    smoother.update(5,1,'A')
    with pytest.raises(ValueError,match='once'):
        smoother.update(5,1,'B')
    with pytest.raises(ValueError,match='backwards'):
        smoother.advance(4)
    with pytest.raises(ValueError,match='role'):
        smoother.update(6,1,'other')


@pytest.mark.parametrize('fps',[0,-1,float('nan'),float('inf')])
def test_invalid_fps(fps):
    with pytest.raises(ValueError):
        TrackRoleSmoother(fps)
