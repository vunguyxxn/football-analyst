import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import cv2
import numpy as np
import pytest

from backend.cv import prepare_video_review as review


def setup_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(review, 'ROOT', tmp_path)
    source=tmp_path/'source.mp4'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(96,64))
    assert writer.isOpened()
    for i in range(12):writer.write(np.full((64,96,3),i*15,dtype=np.uint8))
    writer.release()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    plan={'video':source.name,'raw_video':source.name,'video_sha256':digest,'raw_sha256':digest,
          'raw_frame_offset':0,'fps':10,'image_size':[96,64], 'pitch_m':[105,68],
          'landmarks':[], 'clips':[{'id':'sample','label':'test </script>', 'priority':1,
          'metric_scope':'not_accepted','start_frame':2,'end_frame_exclusive':9,'frames':[3,6]}]}
    path=tmp_path/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
    return source,path,plan


def test_packet_preserves_exact_source_frames_and_exports_no_labels(tmp_path,monkeypatch):
    source,path,plan=setup_packet(tmp_path,monkeypatch)
    packet=review.prepare(path,tmp_path/'packet')
    assert packet['status']=='pending_human_annotation'
    assert packet['source_total_frames']==12
    assert [f['clean_frame'] for f in packet['frames']]==[3,6]
    assert all(not f['reviewed'] and f['annotations']==[] for f in packet['frames'])
    assert all(f['time_s']==f['raw_time_s']==f['clean_frame']/10 for f in packet['frames'])
    cap=cv2.VideoCapture(str(source))
    for i in range(12):
        ok,picture=cap.read();assert ok
        if i in [3,6]:
            stored=cv2.imread(str(tmp_path/'packet'/f'frames/frame_{i:06d}.png'))
            np.testing.assert_array_equal(stored,picture)
    cap.release()
    clip=cv2.VideoCapture(str(tmp_path/'packet/clips/sample.mp4'));count=0
    assert clip.get(cv2.CAP_PROP_FPS)==10
    while clip.read()[0]:count+=1
    clip.release();assert count==7
    assert packet['clips'][0]['frame_count']==7
    html=(tmp_path/'packet/review.html').read_text(encoding='utf-8')
    assert 'test </script>' not in html and 'test \\u003c/script>' in html
    assert '__PACKET_JSON__' not in html
    assert (tmp_path/'packet/annotations_template.csv').read_text(encoding='utf-8-sig').count('\n')==1
    saved=json.loads((tmp_path/'packet/manifest.json').read_text(encoding='utf-8'))
    assert saved==packet


def test_source_replacement_and_existing_annotation_directory_are_guarded(tmp_path,monkeypatch):
    source,path,plan=setup_packet(tmp_path,monkeypatch)
    target=tmp_path/'packet'
    target.mkdir();annotation=target/'annotations_review.json';annotation.write_text('human data')
    with pytest.raises(ValueError,match='new output'):
        review.prepare(path,target)
    assert annotation.read_text()=='human data'
    plan['video_sha256']='wrong';path.write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='hash'):
        review.prepare(path,tmp_path/'bad_hash')
    assert not (tmp_path/'bad_hash').exists()
    with pytest.raises(ValueError,match='inside'):
        review.workspace_path(tmp_path.parent/'outside')


@pytest.mark.parametrize('invalid',['duplicate','outside','offset'])
def test_bad_frame_plan_stops_before_creating_packet(tmp_path,monkeypatch,invalid):
    _,path,plan=setup_packet(tmp_path,monkeypatch)
    if invalid=='duplicate':plan['clips'][0]['frames']=[3,3]
    elif invalid=='outside':plan['clips'][0]['frames']=[99]
    else:plan['raw_frame_offset']=5
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError):review.prepare(path,tmp_path/'invalid')
    assert not (tmp_path/'invalid').exists()


def test_offline_annotation_handlers_without_a_browser():
    node=shutil.which('node')
    if node is None:pytest.skip('Node required for offline annotation UI test')
    result=subprocess.run([node,str(Path(__file__).with_name('video_review_ui_test.cjs')),
                           str(Path(review.__file__).with_name('video_review.html'))],
                          capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
