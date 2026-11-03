"""Read-only API checks for a source-matched, explicitly partial video demo."""
import json
import math
from pathlib import Path

from fastapi.testclient import TestClient
from backend.app.main import app


def verify(job):
    client=TestClient(app)
    data={}
    for name in ['pitch-estimate','pitch-tracking','tactics']:
        response=client.get(f'/api/video-jobs/{job}/{name}')
        response.raise_for_status()
        data[name]=response.json()
    pitch,positions,tactics=data.values()
    errors=[]
    for row in positions:
        if not (math.isfinite(row['x_m']) and math.isfinite(row['y_m']) and 0<=row['x_m']<=105 and 0<=row['y_m']<=68):
            errors.append('Invalid pitch coordinate')
    advice=0
    for window in tactics.get('windows',[]):
        heat=window.get('heatmap_seconds') or []
        if (window['status']=='observed_cluster' and not heat) or not all(math.isfinite(v) and v>=0 for line in heat for v in line):
            errors.append('Missing or invalid heatmap')
        for item in window.get('recommendations',[]):
            advice+=1
            if window['status']!='observed_cluster' or not item.get('condition') or not item.get('evidence'):
                errors.append('Unsupported recommendation')
            for evidence in item.get('evidence',[]):
                value=window['metrics'].get(evidence['metric'])
                if 'index' in evidence and value is not None:value=value[evidence['index']]
                if value!=evidence['value']:errors.append('Evidence differs from metric')
    if not positions or not tactics.get('windows') or not advice:
        errors.append('Empty demo output')
    if pitch['source_sha256']!=tactics['source_sha256']:
        errors.append('Source mismatch')
    return {'job_id':job,'source_sha256':pitch['source_sha256'],'calibrated_seconds':sum(i['end_s']-i['start_s'] for i in pitch['calibrated_intervals']),
            'duration_s':pitch['duration_s'],'position_rows':len(positions),'supported_tactical_windows':sum(w['status']=='observed_cluster' for w in tactics.get('windows',[])),
            'recommendations':advice,'errors':errors,'api_consistency_passed':not errors,
            'scope':'Existing processed job/API readback, not fresh-upload or browser acceptance. Partial provisional calibration; not independently validated tactical accuracy.'}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    result=verify('fc0cd4212aaa436a8614dacd4b74241f')
    (root/'docs/fixtures/demo_flow_readback_v1.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    raise SystemExit(bool(result['errors']))
