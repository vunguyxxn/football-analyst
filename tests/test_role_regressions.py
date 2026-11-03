import numpy as np
from backend.cv.audit_role_regressions import explain, raw_evidence, transition


LABEL={'role':'goalkeeper','xyxy':[10,10,30,50]}


def test_transitions_are_role_specific_and_include_recoveries():
    keeper={'role':'goalkeeper'};player={'role':'player'}
    assert transition('goalkeeper',keeper,player)=='lost'
    assert transition('goalkeeper',player,keeper)=='gained'
    assert transition('referee',keeper,player)=='still_wrong'
    assert transition('goalkeeper',keeper,keeper)=='retained'


def test_low_correct_score_is_not_called_nms_or_localization():
    raw=raw_evidence(LABEL,(np.array([[10,10,30,50]]),np.array([[.8,.15,.05]])))
    assert raw['max_role_score_at_iou50']==.15
    assert raw['best']['argmax_role']=='player'
    assert explain(LABEL,{'role':'player'},[],raw)=='correct_role_score_below_threshold'


def test_single_label_argmax_can_hide_a_high_correct_role_score():
    raw=raw_evidence(LABEL,(np.array([[10,10,30,50]]),np.array([[.8,.4,.05]])))
    assert raw['max_winning_role_score_at_iou50'] is None
    assert explain(LABEL,None,[],raw)=='correct_role_loses_class_argmax'


def test_matching_competition_takes_precedence_over_score_diagnosis():
    correct={'role':'goalkeeper','xyxy':[10,10,30,50],'confidence':.4}
    assert explain(LABEL,None,[correct],{})=='correct_role_box_present_but_matching_competes'


def test_raw_localization_does_not_use_boxes_below_matching_iou():
    raw=raw_evidence(LABEL,(np.array([[200,200,220,240]]),np.array([[.1,.9,.05]])))
    assert raw['best'] is None
    assert explain(LABEL,None,[],raw)=='no_raw_box_at_iou50'


def test_winning_box_absent_after_postprocessing_is_not_called_low_score():
    raw=raw_evidence(LABEL,(np.array([[10,10,30,50]]),np.array([[.2,.6,.05]])))
    assert raw['max_winning_role_score_at_iou50']==.6
    assert explain(LABEL,None,[],raw)=='winning_correct_raw_box_removed_before_matching'
