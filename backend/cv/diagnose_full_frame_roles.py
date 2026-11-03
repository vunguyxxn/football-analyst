import json
from pathlib import Path
from backend.cv.finetune_roles import setup
from backend.cv.compare_role_models import fixed_confidence
from backend.cv.evaluate_role_detector import checked,digest

def main():
    r=Path(__file__).resolve().parents[2];setup(r);p=json.loads((r/'docs/fixtures/clean_full_frame_roles_v5.json').read_text());dataset=r/'data/processed/clean_full_frame_roles_v5'
    m={'files':[{'split':'val','image':f'images/train/{s["id"]}.jpg','label':f'labels/train/{s["id"]}.txt'} for s in p['sources']]}
    specs=json.loads((r/'docs/fixtures/role_training_protocol_v3.json').read_text())['models'];v3=json.loads((r/'docs/fixtures/role_training_result_v3.json').read_text())['training'];results={}
    for name,path,sha in [('v1',specs[0]['path'],specs[0]['sha256']),('v3',v3['best_weights'],v3['best_weights_sha256'])]:
     results[name]=fixed_confidence(checked(r,path,sha),dataset,m,'val',.25,640)
    report={'scope':'Development-only full-frame diagnostic; gFCS/k13 supplied training ROI in v3. Not independent validation.','results':results,'packet_sha256':digest(r/'docs/fixtures/clean_full_frame_roles_v5.json')}
    (r/'docs/fixtures/clean_full_frame_role_diagnostic_v5.json').write_text(json.dumps(report,indent=2));print(json.dumps(results))

if __name__ == '__main__':
    main()
