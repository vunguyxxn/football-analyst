import json,shutil
from pathlib import Path
from backend.cv.evaluate_role_detector import digest,checked
from backend.cv.prepare_role_dataset import verify_dataset,yaml_text
from backend.cv.balance_role_dataset import protected_rows

def main():
    r=Path(__file__).resolve().parents[2];base=r/'data/processed/role_clean_dataset_v6';m=verify_dataset(r,base,r/'docs/fixtures/role_clean_training_protocol_v6.json');plan={}
    for arm,enabled in [('fixed',False),('multi',True)]:
     p=json.loads((r/'docs/fixtures/role_clean_training_protocol_v6.json').read_text());t=json.loads((r/'docs/fixtures/role_clean_training_result_v6.json').read_text())['training']
     p.update(kind='role_scale_protocol_v7',arm=arm,multi_scale=enabled,image_size=896,evaluation_image_size=640,batch=1,lr0=.0001,initialization='Warm-start clean v6 with fresh AdamW; paired fixed/multi differ only multi_scale',models=[{'id':'small','path':t['best_weights'],'sha256':t['best_weights_sha256']}],source_manifest_sha256=digest(base/'manifest.json'))
     pp=r/f'docs/fixtures/role_scale_{arm}_protocol_v7.json';pp.write_text(json.dumps(p,indent=2));out=r/f'data/processed/role_scale_v7/{arm}_dataset'
     if out.exists():raise FileExistsError(out)
     for row in m['files']:
      for key in ['image','label']:
       target=out/row[key];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(base,row[key],row[key+'_sha256']),target)
     new={**m,'protocol_sha256':digest(pp)};assert protected_rows(new)==protected_rows(m);(out/'manifest.json').write_text(json.dumps(new,indent=2));(out/'data.yaml').write_text(yaml_text(out));verify_dataset(r,out,pp)
     plan[arm]={'protocol':pp.relative_to(r).as_posix(),'protocol_sha256':digest(pp),'dataset':out.relative_to(r).as_posix(),'manifest_sha256':digest(out/'manifest.json')}
    (r/'docs/fixtures/role_scale_plan_v7.json').write_text(json.dumps({'arms':plan,'training_started':False,'data_changes':'None; same 369 exposures and immutable validation/test. Colour inventory incomplete; no claim of newly collected dark referees.','multiscale_range_long_side':[448,1344],'resource_status':'Planned FP32 batch1. Maximum-shape optimizer/loss memory smoke still required before full run.','software_source':'Installed ultralytics 8.3.221 detection train preprocess_batch, boolean multi_scale samples 0.5..1.5 times imgsz aligned to stride32'},indent=2));print('Prepared fixed/multi datasets and frozen protocols')

if __name__=='__main__':main()
