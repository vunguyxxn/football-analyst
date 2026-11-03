import pytest
from backend.cv.finetune_roles import scale_options
from backend.cv.role_distribution import size_bin


def test_old_protocol_remains_fixed_and_new_plan_enables_multiscale():
    assert scale_options({})=={'multi_scale':False}
    assert scale_options({'multi_scale':True,'image_size':896,'batch':1})=={'multi_scale':True}


@pytest.mark.parametrize('value',[.5,'true',1])
def test_installed_boolean_setting_does_not_silently_accept_a_range(value):
    with pytest.raises(ValueError):scale_options({'multi_scale':value})


@pytest.mark.parametrize('size,batch',[(1280,1),(896,4)])
def test_unreviewed_multiscale_resource_envelope_rejected(size,batch):
    with pytest.raises(ValueError):scale_options({'multi_scale':True,'image_size':size,'batch':batch})


def test_geometry_bins_have_consistent_boundaries():
    assert [size_bin(h) for h in [23.99,24,47.99,48]]==['under24','24to48','24to48','48plus']
