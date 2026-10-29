import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app import video_jobs
from backend.cv.landmark_guard import LandmarkGuard
from backend.cv.publish_pitch_estimate import digest, publish
from backend.cv.project_uploaded_job import project_job


def case(tmp_path):
    job, candidate = tmp_path/('b'*32), tmp_path/'candidate'
    job.mkdir(); candidate.mkdir()
    (job/'source.mp4').write_bytes(b'fixture video')
    source = digest(job/'source.mp4')
    (job/'status.json').write_text(json.dumps({'status':'completed','result':{'fps':1,'frames':10}}))
    controls = {'source_sha256':source,'anchors':[{'frame':0,'end_frame':10}]}
    checks = {'source_sha256':source,'max_error_m':1,'max_gap_frames':5,
              'checkpoints':[{'frame':frame,'image_points':[[1,2],[3,4]]} for frame in (1,5,9)]}
    calibration, protocol = tmp_path/'calibration.json', tmp_path/'checks.json'
    calibration.write_text(json.dumps(controls)); protocol.write_text(json.dumps(checks))
    rows = [{'frame':frame,'time_s':frame,'track_id':1,'team':'A','x_m':50,'y_m':34} for frame in range(1,10)]
    (candidate/'tracking.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))
    report = {'kind':'uploaded_pitch_estimate_v1','person_job_id':job.name,'source_sha256':source,
              'pitch_m':[105,68],'origin':'bottom_left','duration_s':10,
              'input_sha256':{'calibration':digest(calibration),'landmark_checks':digest(protocol)},
              'segments':[{'segment':0,'start_s':0.,'end_s':10.}],
              'calibrated_intervals':[{'start_s':1.,'end_s':10.}],
              'accepted_positions':9,'frames_with_positions':9,
              'landmark_checks':{'enabled':True,'independently_validated':False,
                                 'results':[{'frame':frame,'status':'verified','errors_m':[.1,.2],
                                             'limit_m':1,'max_error_m':.2} for frame in (1,5,9)]}}
    (candidate/'report.json').write_text(json.dumps(report))
    previous = job/'pitch_estimate'
    previous.mkdir(); (previous/'report.json').write_bytes(b'previous report'); (previous/'tracking.jsonl').write_bytes(b'previous rows')
    return job,candidate,calibration,protocol,report


def test_publish_retains_previous_pair_and_api_checks_tracking_hash(tmp_path,monkeypatch):
    job,candidate,calibration,protocol,_ = case(tmp_path)
    result = publish(job,candidate,calibration,protocol)
    backup = Path(result['backup'])
    assert (backup/'report.json').read_bytes() == b'previous report'
    assert (backup/'tracking.jsonl').read_bytes() == b'previous rows'
    assert (job/'pitch_estimate/tracking.jsonl').read_bytes() == (candidate/'tracking.jsonl').read_bytes()
    report = json.loads((job/'pitch_estimate/report.json').read_text())
    assert report['publication']['tracking_sha256'] == digest(candidate/'tracking.jsonl')
    assert report['publication']['independently_validated'] is False
    monkeypatch.setattr(video_jobs,'ROOT',tmp_path)
    client = TestClient(app)
    url = f'/api/video-jobs/{job.name}/pitch-tracking'
    assert len(client.get(url).json()) == 9
    (job/'pitch_estimate/tracking.jsonl').write_text('')
    assert client.get(url).status_code == 422


@pytest.mark.parametrize('invalid',['source','changed_fixture','missing_closing','failed_middle','stale_gap','outside_row','duplicate','counts'])
def test_refuses_invalid_candidate_without_touching_live_pair(tmp_path,invalid):
    job,candidate,calibration,protocol,report = case(tmp_path)
    if invalid == 'source': report['source_sha256'] = 'foreign'
    if invalid == 'changed_fixture': calibration.write_text('{}')
    if invalid == 'missing_closing': report['landmark_checks']['results'].pop()
    if invalid == 'failed_middle': report['landmark_checks']['results'][1]['status'] = 'lost'
    if invalid == 'stale_gap': report['landmark_checks']['results'].pop(1)
    if invalid == 'counts': report['accepted_positions'] = 99
    if invalid in ('outside_row','duplicate'):
        rows = (candidate/'tracking.jsonl').read_text().splitlines()
        if invalid == 'duplicate': rows.append(rows[0])
        else:
            row = json.loads(rows[0]); row['frame']=0; row['time_s']=0
            rows[0]=json.dumps(row)
        (candidate/'tracking.jsonl').write_text('\n'.join(rows))
    (candidate/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError): publish(job,candidate,calibration,protocol)
    assert (job/'pitch_estimate/report.json').read_bytes() == b'previous report'
    assert not list(job.glob('pitch-estimate-backup-*'))


def test_install_failure_restores_previous_result(tmp_path,monkeypatch):
    job,candidate,calibration,protocol,_ = case(tmp_path)
    original = Path.rename
    def fail_stage(self,target):
        if self.name.startswith('pitch-estimate-stage-'):
            raise OSError('simulated locked directory')
        return original(self,target)
    monkeypatch.setattr(Path,'rename',fail_stage)
    with pytest.raises(OSError): publish(job,candidate,calibration,protocol)
    assert (job/'pitch_estimate/report.json').read_bytes() == b'previous report'
    assert (job/'pitch_estimate/tracking.jsonl').read_bytes() == b'previous rows'


def test_expanded_fixture_keeps_thresholds_and_isolates_rejected_checkpoints():
    root = Path(__file__).resolve().parents[1]
    old = json.loads((root/'docs/fixtures/clip_f51735_manual_pitch_v2.json').read_text())
    controls = json.loads((root/'docs/fixtures/clip_f51735_manual_pitch_v4.json').read_text())
    path = root/'docs/fixtures/clip_f51735_landmark_checks_v4.json'
    checks = json.loads(path.read_text())
    ranges = [(a['frame'],a['end_frame']) for a in controls['anchors']]
    guard = LandmarkGuard(path,controls['source_sha256'],1920,1080,ranges)
    assert guard.limit == 1 and guard.max_gap == 150
    assert controls['anchors'][4:6] == old['anchors']
    assert ranges[1] == (300,451)  # do not retain extrapolation after last passing check
    for anchor in controls['anchors']:
        if 'image_points' in anchor: assert anchor['max_check_error_px'] == 10
    assert checks['excluded_checkpoints'][0]['frame'] == 599
    for frame in (601,):
        checkpoint = next(c for c in checks['checkpoints'] if c['frame']==frame)
        assert {point[0] for point in checkpoint['pitch_points']} == {52.5,88.5}


@pytest.mark.parametrize('mutate',[False,True])
def test_projection_records_inputs_and_detects_changes_during_processing(tmp_path,monkeypatch,mutate):
    import numpy as np
    import backend.cv.project_uploaded_job as module
    job=tmp_path/'job'; job.mkdir()
    (job/'source.mp4').write_bytes(b'capture fixture')
    (job/'status.json').write_text(json.dumps({'status':'completed','result':{'fps':30,'frames':1,'chunks':1,'width':100,'height':100}}))
    (job/'chunk-0.json').write_text(json.dumps({'frames':[{'frame':0,'boxes':[]}]}))
    calibration=tmp_path/'controls.json'
    calibration.write_text(json.dumps({'source_sha256':digest(job/'source.mp4'),'image_size':[100,100],'pitch_m':[105,68],
                                      'anchors':[{'frame':0,'end_frame':1,'image_points':[[0,99],[99,99],[99,0],[0,0]],
                                                  'pitch_points':[[0,0],[105,0],[105,68],[0,68]]}]}))
    class Capture:
        def read(self):
            if mutate: calibration.write_text(calibration.read_text()+' ')
            return True,np.zeros((100,100,3),dtype=np.uint8)
        def release(self): pass
    monkeypatch.setattr(module.cv2,'VideoCapture',lambda _:Capture())
    output=tmp_path/'output'
    if mutate:
        with pytest.raises(ValueError,match='changed during'): project_job(job,calibration,output)
        assert not (output/'report.json').exists()
    else:
        report=project_job(job,calibration,output)
        assert report['input_sha256']=={'calibration':digest(calibration),'landmark_checks':None}
