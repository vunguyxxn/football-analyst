import cv2
import numpy as np
import pytest

from backend.cv.homography import matrix_for, refined_matrix_for


def test_extra_controls_reduce_error_at_independent_ground_points():
    world = np.array([[0,68],[16.5,54.16],[52.5,68],[52.5,0]],float)
    extra = np.array([[52.5,43.15],[52.5,24.85]],float)
    camera = np.array([[12,.5,100],[.1,-6,650],[.002,.003,1.]])
    def project(points,matrix):
        return cv2.perspectiveTransform(np.asarray(points,float)[:,None],matrix)[:,0]
    image=project(world,camera)
    image[:,1]+=[2,-1,1,0]
    extra_image=project(extra,camera)
    original=matrix_for(image,world)
    refined=refined_matrix_for(image,world,extra_image,extra)
    independent=np.array([[40,30],[50,40],[45,45],[55,20]],float)
    pixels=project(independent,camera)
    before=np.linalg.norm(project(pixels,original)-independent,axis=1).mean()
    after=np.linalg.norm(project(pixels,refined)-independent,axis=1).mean()
    assert after < before
    assert after < .2


@pytest.mark.parametrize('image,pitch',[
    ([[1,1]],[[1,1]]),
    ([[1,1],[2,2]],[[1,1]]),
    ([[1,1],[2,2]],[[1,1],[106,2]]),
    ([[1,1],[float('nan'),2]],[[1,1],[2,2]]),
    ([[1,1],[1,1]],[[1,1],[2,2]]),
    ([[1,1],[2,2]],[[1,1],[1,1]]),
    (None,None),
])
def test_invalid_extra_controls_are_rejected(image,pitch):
    with pytest.raises(ValueError):
        refined_matrix_for([[0,0],[105,0],[105,68],[0,68]],
                           [[0,0],[105,0],[105,68],[0,68]],image,pitch)


def test_loader_uses_extra_controls_and_rejects_off_image(tmp_path):
    import hashlib
    import json
    from backend.cv.homography import PitchCalibration
    source=tmp_path/'source.mp4';source.write_bytes(b'identity')
    path=tmp_path/'calibration.json'
    base=[[0,67],[104,67],[104,0],[0,0]]
    world=[[0,0],[105,0],[105,68],[0,68]]
    payload={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'image_size':[105,68],'segments':[{'start_frame':0,'end_frame':10,
             'image_points':base,'pitch_points':world,
             'extra_image_points':[[52,20],[52,40]],
             'extra_pitch_points':[[52.5,48],[52.5,28]]}]}
    path.write_text(json.dumps(payload))
    calibration=PitchCalibration(source,path,105,68)
    expected=refined_matrix_for(base,world,[[52,20],[52,40]],[[52.5,48],[52.5,28]])
    assert calibration.segments[0][3] == pytest.approx(expected)
    payload['segments'][0]['extra_image_points'][0][0]=106
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='outside image'):
        PitchCalibration(source,path,105,68)
