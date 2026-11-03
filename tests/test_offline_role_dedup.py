import copy
import pytest
from backend.cv.offline_role_dedup import suppress_cross_role


def box(role,score,x=0):
    return {'role':role,'confidence':score,'xyxy':[x,0,x+10,20]}


def test_cross_role_chooses_score_not_preferred_role_and_does_not_mutate():
    rows=[box('player',.6),box('goalkeeper',.9),box('referee',.8,100)]
    old=copy.deepcopy(rows)
    kept,removed=suppress_cross_role(rows)
    assert kept==[rows[1],rows[2]]
    assert removed==[{'removed_index':0,'winner_index':1}]
    assert rows==old


def test_nearby_people_and_same_role_not_suppressed():
    rows=[box('player',.9),box('referee',.8,3),box('player',.7)]
    assert suppress_cross_role(rows)==(rows,[])


def test_suppressed_box_cannot_suppress_another_person_transitively():
    rows=[box('player',.9),box('referee',.8,1),box('goalkeeper',.7,2)]
    kept,_=suppress_cross_role(rows)
    assert kept==[rows[0],rows[2]]


def test_ties_stable_and_survivors_keep_input_order_for_matching():
    rows=[box('player',.6,100),box('referee',.9),box('goalkeeper',.9)]
    assert suppress_cross_role(rows)[0]==rows[:2]


@pytest.mark.parametrize('threshold',[-.1,1.1])
def test_invalid_overlap_rejected(threshold):
    with pytest.raises(ValueError):suppress_cross_role([],threshold)
