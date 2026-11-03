"""Offline cross-role suppression diagnostic; no runtime or matching changes."""
from collections import Counter
import json
from pathlib import Path

from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest, iou
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def suppress_cross_role(predictions, threshold=.7):
    """Keep higher-confidence boxes; suppress only overlapping different roles."""
    if not 0 <= threshold <= 1:raise ValueError('Invalid overlap threshold')
    kept=[];removed=[]
    for index in sorted(range(len(predictions)),key=lambda i:(-predictions[i]['confidence'],i)):
        current=predictions[index]
        winner=next((j for j in kept if predictions[j]['role']!=current['role']
                     and iou(predictions[j]['xyxy'],current['xyxy'])>threshold),None)
        if winner is None:kept.append(index)
        else:removed.append({'removed_index':index,'winner_index':winner})
    # Preserve original ordering for the frozen greedy role-blind matching.
    return [predictions[i] for i in sorted(kept)],removed


def main(root):
    import cv2
    setup(root)
    from ultralytics import YOLO
    dataset=root/'data/processed/role_clean_dataset_v6'
    protocol=root/'docs/fixtures/role_clean_training_protocol_v6.json'
    manifest=verify_dataset(root,dataset,protocol)
    frozen=json.loads((root/'docs/fixtures/role_resolution_result_v6.json').read_text())
    training=json.loads((root/'docs/fixtures/role_clean_training_result_v6.json').read_text())['training']
    weights=checked(root,training['best_weights'],frozen['weights_sha256'])
    output=root/'data/processed/offline_role_dedup_v6';output.mkdir(exist_ok=False)
    model=YOLO(str(weights))
    if list(model.names.values())!=NAMES:raise ValueError('Unexpected roles')
    results={};events=[]
    for split in ['val','test']:
        states={name:{'confusion':Counter(),'extras':Counter()} for name in ['original','deduplicated']}
        keeper_transitions=Counter();suppression_pairs=Counter()
        for row in manifest['files']:
            if row['split']!=split:continue
            image=cv2.imread(str(dataset/row['image']));height,width=image.shape[:2];labels=[]
            for line in (dataset/row['label']).read_text().splitlines():
                role,x,y,w,h=map(float,line.split());labels.append({'role':NAMES[int(role)],'xyxy':[(x-w/2)*width,(y-h/2)*height,(x+w/2)*width,(y+h/2)*height]})
            pred=model.predict(image,imgsz=1280,conf=.25,iou=.7,max_det=300,device=0,half=False,verbose=False)[0]
            predictions=[{'role':NAMES[int(role)],'xyxy':box,'confidence':score} for box,role,score in zip(pred.boxes.xyxy.cpu().tolist(),pred.boxes.cls.cpu().tolist(),pred.boxes.conf.cpu().tolist())]
            filtered,removed=suppress_cross_role(predictions)
            for item in removed:
                loser,winner=predictions[item['removed_index']],predictions[item['winner_index']]
                suppression_pairs[f'{loser["role"]}->{winner["role"]}']+=1
            if removed:events.append({'image':row['image'],'split':split,'predictions':predictions,'suppressed':removed})
            for name,ps in [('original',predictions),('deduplicated',filtered)]:
                counts,extras=frame_confusion(labels,ps)
                states[name]['confusion'].update(counts);states[name]['extras'].update(extras)
            from backend.cv.evaluate_role_detector import match
            before,after=match(labels,predictions,box_iou=.5),match(labels,filtered,box_iou=.5)
            for a,b in zip(before,after):
                if a['role']!='goalkeeper':continue
                correct=lambda r:bool(r['prediction'] and r['prediction']['role']=='goalkeeper')
                keeper_transitions['retained' if correct(a) and correct(b) else 'lost' if correct(a) else 'gained' if correct(b) else 'still_wrong']+=1
        results[split]={name:operating_metrics(s['confusion'],s['extras']) for name,s in states.items()}
        for key in ['confusion','unmatched_predictions','player_called_referee']:
            if results[split]['original'][key]!=frozen['reports'][split]['1280'][key]:raise ValueError('1280 baseline mismatch')
        results[split]['keeper_transitions']=dict(keeper_transitions)
        results[split]['suppression_pairs']=dict(suppression_pairs)
        print(split,json.dumps(results[split]),flush=True)
    verify_dataset(root,dataset,protocol)
    if digest(weights)!=frozen['weights_sha256']:raise ValueError('Weights changed')
    report={'policy':'Greedy confidence-ordered cross-role IoU>0.7 suppression after existing per-class NMS; no role priority. Same-class boxes preserved. Parameters fixed before run, not swept.',
            'confidence':.25,'resolution':1280,'nms_iou':.7,'matching_iou':.5,'results':results,'weights_sha256':digest(weights),
            'manifest_sha256':digest(dataset/'manifest.json'),'pipeline_promoted':False,'training_performed':False,
            'limitation':'Known validation/regression test, non-independent labels. No matching changes; suppression may remove distinct overlapping people. Offline diagnostic only.'}
    (output/'result.json').write_text(json.dumps(report,indent=2))
    (output/'suppression-events.json').write_text(json.dumps(events,indent=2))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
