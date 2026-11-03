import pytest
from backend.cv.release_role_sources import match_splits, verify_frame, verify_increment


def test_entire_match_cannot_cross_split_even_when_clip_or_half_changes():
    with pytest.raises(ValueError,match='Same match'):
        match_splits([{'match_id':'10','split':'train_candidate','clip':'h1_c000'},
                      {'match_id':'10','split':'heldout_review','clip':'h2_c100'}])


def test_heldout_frame_cannot_be_relabelled_as_train():
    with pytest.raises(ValueError,match='split differs'):
        verify_frame({'match_id':'20','split':'train_candidate'},{'20':'heldout_review'})


def test_crop_scoped_annotations_use_roi_geometry_not_unreviewed_pixels():
    f={'match_id':'10','split':'train_candidate','review_status':'agent_reviewed','roi':[0,50,1280,720],
       'objects':[{'id':'g','role':'goalkeeper','xyxy':[100,100,140,180]}]}
    row=verify_frame(f,{'10':'train_candidate'}).split()
    assert row[0]=='1'
    assert float(row[2])==pytest.approx(90/670)
    f['objects'][0]['xyxy'][1]=40
    with pytest.raises(ValueError):verify_frame(f,{'10':'train_candidate'})


def test_increment_rejects_old_frame_even_with_different_roi():
    old={'source_split_sha256':'locked','frames':[{'match_id':'10','frame':125}]}
    new={'source_split_sha256':'locked','frames':[{'match_id':'10','frame':125,'roi':[0,0,100,100]}]}
    with pytest.raises(ValueError,match='Repeated'):verify_increment(new,old)
    new['frames'][0]['frame']=250
    verify_increment(new,old)
    new['source_split_sha256']='changed'
    with pytest.raises(ValueError,match='locked source split'):verify_increment(new,old)


def test_increment_rejects_duplicate_new_frames():
    packet={'source_split_sha256':'locked','frames':[{'match_id':'10','frame':250}]*2}
    with pytest.raises(ValueError,match='Repeated'):
        verify_increment(packet,{'source_split_sha256':'locked','frames':[]})
