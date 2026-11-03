"""Per-label v6/v10 val regressions at frozen thresholds, with raw-head diagnostics."""
from collections import Counter
import json
from pathlib import Path

from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest, iou, match
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def transition(role,before,after):
    a=bool(before and before['role']==role);b=bool(after and after['role']==role)
    return 'retained' if a and b else 'lost' if a else 'gained' if b else 'still_wrong'


def explain(label,after,predictions,raw):
    """Observable inference-stage evidence, not a causal explanation of training."""
    correct=[p for p in predictions if p['role']==label['role'] and iou(label['xyxy'],p['xyxy'])>=.5]
    if correct:return 'correct_role_box_present_but_matching_competes'
    if raw['max_role_score_at_iou50'] is None:return 'no_raw_box_at_iou50'
    if raw['max_role_score_at_iou50']<.25:return 'correct_role_score_below_threshold'
    if raw['max_winning_role_score_at_iou50'] is None:return 'correct_role_loses_class_argmax'
    return 'winning_correct_raw_box_removed_before_matching'


def raw_head(model,image,torch):
    from ultralytics.utils import ops
    with torch.inference_mode():
        tensor=model.predictor.preprocess([image])
        output=model.predictor.inference(tensor)
        if isinstance(output,(tuple,list)):output=output[0]
        if output.ndim!=3 or output.shape[1]!=7:raise ValueError('Unexpected three-role YOLO raw output')
        values=output[0].transpose(0,1)
        boxes=ops.scale_boxes(tensor.shape[2:],ops.xywh2xyxy(values[:,:4]).clone(),image.shape[:2])
        return boxes.cpu().numpy(),values[:,4:].cpu().numpy()


def raw_evidence(label,head):
    import numpy as np
    boxes,scores=head;a,b,c,d=label['xyxy']
    intersection=np.maximum(0,np.minimum(boxes[:,2],c)-np.maximum(boxes[:,0],a))*np.maximum(0,np.minimum(boxes[:,3],d)-np.maximum(boxes[:,1],b))
    areas=(boxes[:,2]-boxes[:,0])*(boxes[:,3]-boxes[:,1])
    overlap=intersection/np.maximum(areas+(c-a)*(d-b)-intersection,1e-9)
    indices=np.flatnonzero(overlap>=.5);role=NAMES.index(label['role'])
    if not len(indices):return {'max_role_score_at_iou50':None,'max_winning_role_score_at_iou50':None,'best':None}
    best=int(indices[np.argmax(scores[indices,role])]);winning=indices[(scores[indices].argmax(axis=1)==role)&(scores[indices,role]>=.25)]
    return {'max_role_score_at_iou50':float(scores[best,role]),
            'max_winning_role_score_at_iou50':float(scores[winning,role].max()) if len(winning) else None,
            'best':{'xyxy':boxes[best].tolist(),'iou':float(overlap[best]),
                    'scores':dict(zip(NAMES,map(float,scores[best]))),'argmax_role':NAMES[int(scores[best].argmax())]}}


def main(root):
    import cv2
    import numpy as np
    torch=setup(root)
    from ultralytics import YOLO
    pp=root/'docs/fixtures/role_sources_training_protocol_v10.json';p=json.loads(pp.read_text())
    rp=root/'docs/fixtures/role_sources_training_result_v10.json';frozen=json.loads(rp.read_text())
    if digest(pp)!=frozen['protocol_sha256']:raise ValueError('Frozen protocol changed')
    dataset=root/p['dataset'];checked(dataset,'manifest.json',frozen['manifest_sha256'])
    manifest=verify_dataset(root,dataset,pp)
    specs={'v6':p['comparison_baseline'], 'v10':{'path':frozen['training']['best_weights'],'sha256':frozen['training']['best_weights_sha256']}}
    paths={n:checked(root,s['path'],s['sha256']) for n,s in specs.items()}
    models={n:YOLO(str(path)) for n,path in paths.items()}
    if any(list(m.names.values())!=NAMES for m in models.values()):raise ValueError('Role IDs changed')
    out=root/'data/processed/role_regressions_audit_v10';out.mkdir(exist_ok=False)
    rows=[];totals={str(s):{n:[Counter(),Counter()] for n in models} for s in [640,1280]}
    for item in manifest['files']:
        if item['split']!='val':continue
        image=cv2.imread(str(dataset/item['image']));h,w=image.shape[:2];labels=[]
        for index,line in enumerate((dataset/item['label']).read_text().splitlines()):
            cls,x,y,bw,bh=map(float,line.split())
            labels.append({'id':index,'role':NAMES[int(cls)],'xyxy':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
        for size in [640,1280]:
            predictions={};paired={}
            for name,model in models.items():
                pred=model.predict(image,imgsz=size,conf=.25,iou=.7,max_det=300,device=0,half=False,verbose=False)[0]
                predictions[name]=[{'id':i,'role':NAMES[int(role)],'xyxy':box,'confidence':score}
                    for i,(box,role,score) in enumerate(zip(pred.boxes.xyxy.cpu().tolist(),pred.boxes.cls.cpu().tolist(),pred.boxes.conf.cpu().tolist()))]
                paired[name]=match(labels,predictions[name],box_iou=.5)
                confusion,extras=frame_confusion(labels,predictions[name]);totals[str(size)][name][0].update(confusion);totals[str(size)][name][1].update(extras)
            pending=[]
            for index,label in enumerate(labels):
                if label['role']=='player':continue
                before,after=(paired[n][index]['prediction'] for n in ['v6','v10'])
                row={'image':item['image'],'image_sha256':item['image_sha256'],'label_sha256':item['label_sha256'],
                     'label_id':index,'role':label['role'],'xyxy':label['xyxy'],'size':size,
                     'height_at_size':(label['xyxy'][3]-label['xyxy'][1])*size/max(w,h),
                     'transition':transition(label['role'],before,after),'v6':before,'v10':after}
                for name in ['v6','v10']:
                    if row[name]:row[name]={**row[name],'matched_iou':iou(label['xyxy'],row[name]['xyxy'])}
                if row['transition']=='lost':pending.append((row,label))
                rows.append(row)
            if pending:
                heads={n:raw_head(m,image,torch) for n,m in models.items()}
                for row,label in pending:
                    row['raw']={n:raw_evidence(label,head) for n,head in heads.items()}
                    row['diagnostic']=explain(label,row['v10'],predictions['v10'],row['raw']['v10'])
                    row['correct_role_high_candidates']=[{**ob,'matched_iou':iou(label['xyxy'],ob['xyxy']),
                        'assigned_label_id':next((a['id'] for a in paired['v10'] if a['prediction'] and a['prediction']['id']==ob['id']),None)}
                        for ob in predictions['v10'] if ob['role']==label['role'] and iou(label['xyxy'],ob['xyxy'])>=.5]
        print(item['image'],flush=True)
    reproduced={size:{n:operating_metrics(*counts) for n,counts in models_counts.items()} for size,models_counts in totals.items()}
    for size,values in reproduced.items():
        for name,value in values.items():
            expected=frozen['models'][name]['validation_'+size]
            if any(value[k]!=expected[k] for k in ['classes','confusion','unmatched_predictions']):raise ValueError('Frozen all-class val totals not reproduced')
    lost=[r for r in rows if r['transition']=='lost']
    for index,row in enumerate(lost):
        row['review_id']=index;im=cv2.imread(str(dataset/row['image']));h,w=im.shape[:2]
        a,b,c,d=map(int,row['xyxy']);x,y=max(0,a-65),max(0,b-65)
        patch=im[y:min(h,d+65),x:min(w,c+65)].copy()
        for box,col in [(row['xyxy'],(0,255,0))]+[(row[n]['xyxy'],col) for n,col in [('v6',(255,160,0)),('v10',(0,0,255))] if row[n]]:
            q=list(map(int,box));cv2.rectangle(patch,(q[0]-x,q[1]-y),(q[2]-x,q[3]-y),col,1)
        scale=min(235/patch.shape[1],180/patch.shape[0]);patch=cv2.resize(patch,None,fx=scale,fy=scale)
        tile=np.full((250,250,3),30,np.uint8);tile[30:30+patch.shape[0],:patch.shape[1]]=patch
        cv2.putText(tile,f'{index} {row["role"]} {row["size"]}',(3,18),0,.46,(255,255,255),1)
        cv2.putText(tile,f'-> {(row["v10"] or {}).get("role","missed")} h={row["height_at_size"]:.1f}',(3,238),0,.42,(255,255,255),1)
        cv2.imwrite(str(out/f'crop-{index}.jpg'),tile)
    for start in range(0,len(lost),20):
        tiles=[cv2.imread(str(out/f'crop-{i}.jpg')) for i in range(start,min(start+20,len(lost)))];tiles += [np.zeros((250,250,3),np.uint8)]*(20-len(tiles))
        cv2.imwrite(str(out/f'sheet-{start//20}.jpg'),np.vstack([np.hstack(tiles[i:i+5]) for i in range(0,20,5)]))
    summary={}
    for size in [640,1280]:
        summary[str(size)]={}
        for role in ['goalkeeper','referee']:
            subset=[r for r in rows if r['size']==size and r['role']==role];bad=[r for r in subset if r['transition']=='lost']
            summary[str(size)][role]={'labels':len(subset),'transitions':dict(Counter(r['transition'] for r in subset)),
                'lost_destinations':dict(Counter((r['v10'] or {}).get('role','missed') for r in bad)),
                'diagnostics':dict(Counter(r['diagnostic'] for r in bad)),
                'lost_size_bins':dict(Counter('under24' if r['height_at_size']<24 else '24to48' if r['height_at_size']<48 else '48plus' for r in bad))}
    verify_dataset(root,dataset,pp)
    for n,path in paths.items():
        if digest(path)!=specs[n]['sha256']:raise ValueError('Weights changed')
    report={'summary':summary,'rows':rows,'reproduced_all_class_validation':reproduced,
            'protocol_sha256':digest(pp),'comparison_result_sha256':digest(rp),'weights':specs,
            'scope':'Val only, all original labels and thresholds preserved, no training or relabelling. Raw post-sigmoid per-class scores before single-label argmax/NMS are diagnostics, not probabilities of correctness. Inference-stage evidence cannot isolate causal effect of added data.'}
    (out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(summary))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
