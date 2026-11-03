"""Paired batch-one FP32 resolution diagnostic with frozen weights and thresholds."""
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def main(root):
    import cv2
    import numpy as np
    torch=setup(root)
    from ultralytics import YOLO
    protocol=root/'docs/fixtures/role_clean_training_protocol_v6.json'
    dataset=root/'data/processed/role_clean_dataset_v6'
    manifest=verify_dataset(root,dataset,protocol)
    reference=json.loads((root/'docs/fixtures/role_clean_training_result_v6.json').read_text())
    spec=reference['training']
    weights=checked(root,spec['best_weights'],spec['best_weights_sha256'])
    output=root/'data/processed/role_resolution_v6'
    output.mkdir(exist_ok=False)
    model=YOLO(str(weights))
    if list(model.names.values())!=NAMES:raise ValueError('Unexpected role map')
    def predict(image,size):
        return model.predict(image,imgsz=size,conf=.25,iou=.7,max_det=300,device=0,half=False,verbose=False)[0]
    first=next(r for r in manifest['files'] if r['split']=='val')
    image=cv2.imread(str(dataset/first['image']))
    for size in [640,1280]:
        for _ in range(3):predict(image,size)
    torch.cuda.synchronize()
    reports={}
    for split in ['val','test']:
        states={size:{'confusion':Counter(),'extras':Counter(),'latency_ms':[],'peak_allocated_mib':0.} for size in [640,1280]}
        frames=0
        for row in manifest['files']:
            if row['split']!=split:continue
            image=cv2.imread(str(dataset/row['image']))
            height,width=image.shape[:2]
            labels=[]
            for line in (dataset/row['label']).read_text().splitlines():
                role,x,y,w,h=map(float,line.split())
                labels.append({'role':NAMES[int(role)],'xyxy':[(x-w/2)*width,(y-h/2)*height,(x+w/2)*width,(y+h/2)*height]})
            # Alternate first resolution to reduce ordering bias; no output-driven tuning.
            for size in ([640,1280] if frames%2==0 else [1280,640]):
                state=states[size]
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
                started=perf_counter();prediction=predict(image,size);torch.cuda.synchronize()
                state['latency_ms'].append((perf_counter()-started)*1000)
                state['peak_allocated_mib']=max(state['peak_allocated_mib'],torch.cuda.max_memory_allocated()/1024**2)
                predictions=[{'role':NAMES[int(role)],'xyxy':box} for box,role in zip(prediction.boxes.xyxy.cpu().tolist(),prediction.boxes.cls.cpu().tolist())]
                counts,extras=frame_confusion(labels,predictions)
                state['confusion'].update(counts);state['extras'].update(extras)
                del prediction
            frames+=1
        reports[split]={}
        for size,state in states.items():
            values=state['latency_ms']
            reports[split][str(size)]={**operating_metrics(state['confusion'],state['extras']), 'frames':frames,
                'speed':{'mean_ms':mean(values),'median_ms':median(values),'p95_ms':float(np.percentile(values,95)),
                         'predict_only_fps':1000/mean(values),'peak_allocated_mib':state['peak_allocated_mib']}}
        frozen=reference['models']['balanced']['validation_fixed_confidence' if split=='val' else 'test_fixed_confidence']
        for key in ['confusion','unmatched_predictions','player_called_referee']:
            if reports[split]['640'][key]!=frozen[key]:raise ValueError('640 regression totals differ from frozen run')
        print(split,json.dumps(reports[split]),flush=True)
    verify_dataset(root,dataset,protocol)
    if digest(weights)!=spec['best_weights_sha256']:raise ValueError('Weights changed')
    result={'kind':'role_resolution_v6','weights_sha256':digest(weights),'manifest_sha256':digest(dataset/'manifest.json'),
            'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,'confidence':.25,'nms_iou':.7,'matching_iou':.5,
            'precision':'FP32','batch':1,'warmup_per_size':3,'reports':reports,'training_performed':False,'pipeline_promoted':False,
            'timing_scope':'Synchronized predict wall time including preprocessing/forward/NMS; excludes file IO, label matching, CPU extraction. Not full video pipeline FPS. CUDA allocated tensor peak excludes reserved and other process memory.',
            'limitation':'Single paired pass, alternating resolution order. Known val/test, provided/agent labels, not independent accuracy or causal proof. No automatic runtime resolution selection.'}
    (output/'result.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
