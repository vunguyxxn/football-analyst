"""Compare a locked small run with frozen references at 640/1280; never deploy."""
import argparse
from collections import Counter
import contextlib
import gc
import json
from pathlib import Path
from time import perf_counter

from backend.cv.compare_role_models import fixed_confidence, operating_metrics, validation_choice
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import evaluate, setup, write_json
from backend.cv.prepare_role_dataset import verify_dataset


def sum_diagnostics(reports):
    confusion=Counter();extras=Counter()
    for report in reports:
        confusion.update({(truth,pred):count for truth,values in report['confusion'].items() for pred,count in values.items()})
        extras.update(report['unmatched_predictions'])
    return {**operating_metrics(confusion,extras),'frames':sum(r['frames'] for r in reports),
            'scope':'Four reviewed ROIs of one source match, COCO-assisted agent labels. Not independent or full-clip accuracy.'}


def prediction_speed(weights,dataset,manifest,size,torch):
    """Fixed 20 old-val images, three warmups; wall time for predict only."""
    import cv2
    from ultralytics import YOLO
    rows=[r for r in manifest['files'] if r['split']=='val'][:20]
    images=[cv2.imread(str(dataset/r['image'])) for r in rows]
    model=YOLO(str(weights))
    kwargs=dict(imgsz=size,conf=.25,iou=.7,max_det=300,device=0,verbose=False)
    for image in images[:3]:model.predict(image,**kwargs)
    torch.cuda.synchronize();start=perf_counter()
    for image in images:model.predict(image,**kwargs)
    torch.cuda.synchronize();seconds=perf_counter()-start
    return {'frames':len(images),'elapsed_s':seconds,'prediction_fps':len(images)/seconds,
            'image_ids':[r['image'] for r in rows],
            'scope':'Single sequential run on first20 old-val images, three warmups; predict preprocessing/inference/NMS included, disk decode excluded. Not full video pipeline FPS.'}


def comparison_specs(protocol, status, version):
    baseline=protocol['comparison_baseline']
    references=protocol.get('comparison_references', {'v6':baseline})
    if 'v6' not in references or version in references or references['v6']['sha256']!=baseline['sha256']:
        raise ValueError('Frozen comparison references changed')
    return {**references, version:{'path':status['best_weights'],'sha256':status['best_weights_sha256']}}


def compare(root, version='v10'):
    if version not in {'v10','v11'}:raise ValueError('Unsupported locked experiment')
    pp=root/f'docs/fixtures/role_sources_training_protocol_{version}.json'
    plan=json.loads((root/f'docs/fixtures/role_sources_training_plan_{version}.json').read_text())
    if digest(pp)!=plan['protocol_sha256']:raise ValueError('Frozen protocol changed')
    p=json.loads(pp.read_text());dataset=root/p['dataset']
    checked(dataset,'manifest.json',plan['manifest_sha256'])
    manifest=verify_dataset(root,dataset,pp)
    run=dataset.parent/'small'
    status=json.loads((run/'status.json').read_text())
    if status['status']!='complete' or status['protocol_sha256']!=digest(pp) or status['manifest_sha256']!=plan['manifest_sha256']:
        raise ValueError('Incomplete or stale run')
    specs=comparison_specs(p,status,version)
    paths={name:checked(root,spec['path'],spec['sha256']) for name,spec in specs.items()}
    releases=[]
    for spec in p['source_releases']:
        d=root/spec['directory'];mp=checked(d,'manifest.json',spec['manifest_sha256'])
        m=json.loads(mp.read_text())
        for row in m['files']:
            for key in ['image','label']:checked(d,row[key],row[key+'_sha256'])
        heldout=[{**r,'split':'test'} for r in m['files'] if r['split']=='heldout_review']
        if any(r['match_id']!='128057' for r in heldout):raise ValueError('Unexpected diagnostic match')
        releases.append((d,{'files':heldout}))
    output=dataset.parent/'comparison';output.mkdir(exist_ok=False)
    torch=setup(root);results={name:{} for name in paths}
    sizes=p['evaluation_lock']['sizes']
    with (output/'evaluation.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for name,path in paths.items():
            for size in sizes:
                results[name][f'validation_ap_{size}']=evaluate(path,dataset,{**p,'evaluation_image_size':size},output,'val',f'{name}_val_ap{size}')
                results[name][f'validation_{size}']=fixed_confidence(path,dataset,manifest,'val',.25,size)
            gc.collect();torch.cuda.empty_cache()
        decision=validation_choice(results['v6']['validation_ap_640'],results[version]['validation_ap_640'],p['validation_gate'])
        decision['candidate_is']=version  # Legacy helper calls the candidate "balanced".
        decision['reference_is']='v6'
        write_json(output/'validation-before-test.json',{'results':results,'decision':decision,
                   'protocol_sha256':digest(pp),'weights':specs,'source_releases':p['source_releases']})
        for name,path in paths.items():
            for size in sizes:
                results[name][f'known_test_{size}']=fixed_confidence(path,dataset,manifest,'test',.25,size)
                reports=[fixed_confidence(path,d,m,'test',.25,size) for d,m in releases]
                results[name][f'source_diagnostic_{size}']=sum_diagnostics(reports)
                results[name][f'speed_{size}']=prediction_speed(path,dataset,manifest,size,torch)
            gc.collect();torch.cuda.empty_cache()
    verify_dataset(root,dataset,pp)
    for spec in p['source_releases']:
        checked(root,spec['packet'],spec['packet_sha256'])
        d=root/spec['directory']
        m=json.loads(checked(d,'manifest.json',spec['manifest_sha256']).read_text())
        for row in m['files']:
            for key in ['image','label']:checked(d,row[key],row[key+'_sha256'])
    for name,path in paths.items():
        if digest(path)!=specs[name]['sha256']:raise ValueError('Weights changed')
    result={'kind':f'role_sources_training_result_{version}','protocol_sha256':digest(pp),
            'manifest_sha256':plan['manifest_sha256'],'training':status,'models':results,
            'selection_vs_v6':decision,'pipeline_promoted':False,'independently_validated':False,
            'old_test_previously_inspected':True,'source_diagnostic_previously_partly_inspected':True,
            'scope':p['experiment_scope'],'sampling':p['sampling_lock'],'evaluation':p['evaluation_lock']}
    write_json(output/'result.json',result)
    print(json.dumps({'selection':decision,'weights_sha256':status['best_weights_sha256']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',choices=['v10','v11'],default='v10')
    compare(Path(__file__).resolve().parents[2],parser.parse_args().version)
