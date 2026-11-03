"""Per-label keeper transitions; low-confidence probes are diagnostic only."""
from collections import Counter
import json
from pathlib import Path

from backend.cv.evaluate_role_detector import checked, digest, iou, match
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def transition(before, after):
    a=before is not None and before['role']=='goalkeeper'
    b=after is not None and after['role']=='goalkeeper'
    return 'retained' if a and b else 'lost' if a else 'gained' if b else 'still_wrong'


def main(root):
    import cv2
    import numpy as np
    setup(root)
    from ultralytics import YOLO
    dataset=root/'data/processed/role_clean_dataset_v6'
    manifest=verify_dataset(root,dataset,root/'docs/fixtures/role_clean_training_protocol_v6.json')
    result=json.loads((root/'docs/fixtures/role_resolution_result_v6.json').read_text())
    training=json.loads((root/'docs/fixtures/role_clean_training_result_v6.json').read_text())['training']
    weights=checked(root,training['best_weights'],result['weights_sha256'])
    model=YOLO(str(weights))
    if list(model.names.values())!=NAMES:raise ValueError('Unexpected role mapping')
    output=root/'data/processed/keeper_resolution_audit_v6_checked'
    output.mkdir(exist_ok=False)
    def predict(image,size,confidence):
        p=model.predict(image,imgsz=size,conf=confidence,iou=.7,max_det=300,device=0,half=False,verbose=False)[0]
        return [{'role':NAMES[int(role)],'xyxy':box,'confidence':score} for box,role,score in zip(p.boxes.xyxy.cpu().tolist(),p.boxes.cls.cpu().tolist(),p.boxes.conf.cpu().tolist())]
    rows=[]
    for item in manifest['files']:
        if item['split'] not in ['val','test']:continue
        text=(dataset/item['label']).read_text().splitlines()
        if not any(line.split()[0]=='1' for line in text):continue
        image=cv2.imread(str(dataset/item['image']));h,w=image.shape[:2];labels=[]
        for index,line in enumerate(text):
            role,x,y,bw,bh=map(float,line.split())
            labels.append({'id':index,'role':NAMES[int(role)],'xyxy':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
        predictions={str(size):predict(image,size,.25) for size in [640,1280]}
        paired={size:match(labels,ps,box_iou=.5) for size,ps in predictions.items()}
        probe=None
        for i,label in enumerate(labels):
            if label['role']!='goalkeeper':continue
            before,after=paired['640'][i]['prediction'],paired['1280'][i]['prediction']
            kind=transition(before,after)
            row={'image':item['image'],'split':item['split'],'label_id':i,'xyxy':label['xyxy'],
                 'height_at_640':(label['xyxy'][3]-label['xyxy'][1])*640/max(w,h),'transition':kind,
                 '640':before,'1280':after}
            for size in ['640','1280']:
                if row[size]:row[size]={**row[size],'matched_iou':iou(label['xyxy'],row[size]['xyxy'])}
            if kind=='lost':
                high_keepers=[p for p in predictions['1280'] if p['role']=='goalkeeper']
                high=max(high_keepers,key=lambda p:iou(label['xyxy'],p['xyxy']),default=None)
                row['high_conf_keeper_candidate']=({**high,'iou':iou(label['xyxy'],high['xyxy'])} if high else None)
                if probe is None:probe=predict(image,1280,.001)
                keepers=[p for p in probe if p['role']=='goalkeeper']
                best=max(keepers,key=lambda p:iou(label['xyxy'],p['xyxy']),default=None)
                row['low_conf_keeper_candidate']=({**best,'iou':iou(label['xyxy'],best['xyxy'])} if best else None)
                row['diagnostic']='matched_wrong_role' if after else 'no_match_at_iou_0.5'
            rows.append(row)
    summary={}
    for split in ['val','test']:
        selected=[r for r in rows if r['split']==split]
        summary[split]={'labels':len(selected),'transitions':dict(Counter(r['transition'] for r in selected)),
                        'lost_destinations':dict(Counter((r['1280'] or {}).get('role','no_match') for r in selected if r['transition']=='lost'))}
        for size in ['640','1280']:
            actual=sum(bool(r[size] and r[size]['role']=='goalkeeper') for r in selected)
            if actual!=result['reports'][split][size]['classes']['goalkeeper']['tp']:raise ValueError('Frozen keeper TP totals not reproduced')
    # Every lost keeper, including test regressions, gets a context overlay.
    lost=[r for r in rows if r['transition']=='lost']
    tiles=[]
    for index,row in enumerate(lost):
        row['review_id']=index
        image=cv2.imread(str(dataset/row['image']));h,w=image.shape[:2]
        a,b,c,d=map(int,row['xyxy']);x,y=max(0,a-40),max(0,b-40)
        patch=image[y:min(h,d+40),x:min(w,c+40)].copy()
        for box,color in [(row['xyxy'],(0,255,0))]+[(row[size]['xyxy'],color) for size,color in [('640',(255,160,0)),('1280',(0,0,255))] if row[size]]:
            q=[int(v) for v in box];cv2.rectangle(patch,(q[0]-x,q[1]-y),(q[2]-x,q[3]-y),color,1)
        scale=min(205/patch.shape[1],155/patch.shape[0]);patch=cv2.resize(patch,None,fx=scale,fy=scale)
        tile=np.full((220,220,3),30,np.uint8);tile[30:30+patch.shape[0],:patch.shape[1]]=patch
        role=(row['1280'] or {}).get('role','no_match')
        cv2.putText(tile,f'{index} {row["split"]} -> {role}',(2,18),0,.42,(255,255,255),1)
        cv2.putText(tile,f'h640 {row["height_at_640"]:.1f}px',(2,208),0,.42,(255,255,255),1)
        tiles.append(tile)
    for start in range(0,len(tiles),20):
        group=tiles[start:start+20];group+=[np.zeros((220,220,3),np.uint8)]*(20-len(group))
        cv2.imwrite(str(output/f'sheet-{start//20}.jpg'),np.vstack([np.hstack(group[i:i+5]) for i in range(0,20,5)]))
    verify_dataset(root,dataset,root/'docs/fixtures/role_clean_training_protocol_v6.json')
    if digest(weights)!=result['weights_sha256']:raise ValueError('Weights changed')
    report={'summary':summary,'rows':rows,'weights_sha256':digest(weights),'confidence':.25,'probe_confidence':.001,
            'note':'Same frozen labels and matching. Probe is post-NMS at low confidence, not raw class scores or deployment threshold. No retraining or relabelling.'}
    (output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
