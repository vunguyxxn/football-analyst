import pytest
from backend.cv.audit_role_train_coverage import cluster_boxes, parent_box, unique_train, validate_review


def test_repeated_images_are_exposures_not_new_train_units():
    rows=[{'split':'train','pixel_sha256':'p','label_sha256':'l'}]*4
    rows += [{'split':'val','pixel_sha256':'v','label_sha256':'l'}]
    assert [len(g) for g in unique_train(rows)]==[4]


def test_same_pixels_with_different_labels_stay_distinct_units():
    rows=[{'split':'train','pixel_sha256':'p','label_sha256':label} for label in ['a','b']]
    assert len(unique_train(rows))==2


def test_crop_geometry_returns_to_parent_without_enlarging_the_source_target():
    assert parent_box([2,3,20,61],[377,106,400,169])==[379,109,397,167]
    # 58px target is small in1920-wide source but huge in63px-long crop.
    assert 58*640/1920<24
    assert 58*640/63>500


def box(id,parent,role='referee',xyxy=None):
    return {'id':id,'parent':parent,'role':role,'parent_xyxy':xyxy or [10,10,30,50],
            'source_height640':13.,'family':'scene','exposures':4}


def test_overlapping_crops_do_not_inflate_source_frame_box_clusters():
    groups=cluster_boxes([box('a','p'),box('b','p',xyxy=[11,10,30,50])])
    assert len(groups)==1
    assert set(groups[0]['members'])=={'a','b'}
    assert groups[0]['exposures']==8


def test_other_frames_roles_or_people_are_never_collapsed():
    groups=cluster_boxes([box('a','p'),box('b','q'),box('c','p','goalkeeper'),
                          box('d','p',xyxy=[100,100,130,150])])
    assert len(groups)==4


def test_missing_review_cannot_be_counted_as_absent_coverage():
    with pytest.raises(ValueError,match='exactly once'):
        validate_review([{'id':'g'}],{'objects':[]})


def test_review_binds_the_exact_training_image_and_label():
    ob={'id':'g','image_sha256':'image','label_sha256':'label'}
    rv={**ob,'shirt_appearance':'unknown','context':'not_reviewed_for_position'}
    assert validate_review([ob],{'objects':[rv]})['g']['shirt_appearance']=='unknown'
    with pytest.raises(ValueError,match='different image/label'):
        validate_review([ob],{'objects':[{**rv,'label_sha256':'other'}]})
