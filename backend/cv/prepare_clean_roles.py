import json,shutil,hashlib,cv2
from pathlib import Path
from collections import Counter
from backend.cv.evaluate_role_detector import digest,checked
from backend.cv.prepare_role_dataset import verify_dataset,yaml_text
from backend.cv.balance_role_dataset import protected_rows

def main():
    r=Path(__file__).resolve().parents[2];pp=r/'docs/fixtures/role_clean_training_protocol_v6.json';p=json.loads(pp.read_text());base=r/'data/processed/role_balanced_dataset_v2';m=verify_dataset(r,base,r/'docs/fixtures/role_balance_protocol_v2.json');out=r/'data/processed/role_clean_dataset_v6'
    checked(base,'manifest.json',p['merge_base_manifest_sha256'])
    checked(r,p['clean_full_packet'],p['clean_full_packet_sha256'])
    if out.exists():raise FileExistsError(out)
    rows=list(m['files'])
    for row in rows:
     for key in ['image','label']:
      target=out/row[key];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(base,row[key],row[key+'_sha256']),target)
    packet=json.loads((r/p['clean_full_packet']).read_text());new=r/'data/processed/clean_full_frame_roles_v5';audit=json.loads((new/'manifest.json').read_text());records={a['id']:a for a in audit['files']}
    if p['full_frame_repeats'] != 4:raise ValueError('Locked four-exposure protocol required')
    for s in packet['sources']:
     for rep in range(p['full_frame_repeats']):
      row={'split':'train','family':s['scene_family'],'source':s['sha256'],'provenance':{'reviewed_full_frame':s['id'],'repeat':rep+1}}
      for key,ext,folder in [('image','jpg','images'),('label','txt','labels')]:
       src=checked(new,f'{folder}/train/{s["id"]}.{ext}',records[s['id']][key+'_sha256']);rel=f'{folder}/train/clean-{s["id"]}-{rep+1}.{ext}';shutil.copyfile(src,out/rel);row[key]=rel;row[key+'_sha256']=digest(out/rel)
      im=cv2.imread(str(out/row['image']));row['pixel_sha256']=hashlib.sha256(str(im.shape).encode()+im.tobytes()).hexdigest();rows.append(row)
    result={**m,'kind':'clean_role_dataset_v6','files':rows,'protocol_sha256':digest(pp),'images':dict(Counter(x['split'] for x in rows))}

    if protected_rows(result)!=protected_rows(m):raise ValueError('Protected split changed')
    (out/'manifest.json').write_text(json.dumps(result,indent=2));(out/'data.yaml').write_text(yaml_text(out));verify_dataset(r,out,pp)
    audit={'reviewed_base_images':212,'base_visual_review':'All 212 contact-sheet frames inspected for real camera context; not a fresh per-box annotation or verified match identity audit.','base_manifest_sha256':digest(base/'manifest.json'),'dataset_manifest_sha256':digest(out/'manifest.json'),'full_frame_unique':7,'full_frame_exposures':28,'images':result['images'],'quarantine_base_images_preserved':5,'excluded_media':'No role_counterexamples_v3 ROI merged; no v3 checkpoint reused','initialization_sha256':p['models'][0]['sha256']}
    (r/'docs/fixtures/role_clean_source_audit_v6.json').write_text(json.dumps(audit,indent=2));print(audit)

if __name__=='__main__':
    main()
