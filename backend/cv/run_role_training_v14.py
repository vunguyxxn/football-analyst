"""One locked v14 small run, validation gate before known test, no source diagnostic."""
import argparse
from collections import Counter
import contextlib
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import shutil
import subprocess

from backend.cv.balance_role_dataset import protected_rows
from backend.cv.compare_role_models import fixed_confidence, validation_choice
from backend.cv.compare_role_sources import comparison_specs
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import evaluate, setup, train_one, write_json
from backend.cv.prepare_role_dataset import verify_dataset, yaml_text
from backend.cv.prepare_role_merge_v14 import validate_sampling

PROTOCOL = 'docs/fixtures/role_sources_training_protocol_v14.json'
PLAN = 'docs/fixtures/role_sources_training_plan_v14.json'
RUN = 'data/processed/role_sources_training_v14'
TRAIN_KEYS = ['models','epochs','image_size','batch','amp','optimizer','lr0','seed','workers',
              'mosaic','close_mosaic','multi_scale','selection','test_confidence','test_nms_iou',
              'max_detections','runtime_confidence','validation_gate','evaluation_lock']


def same_configuration(current, reference):
    for key in TRAIN_KEYS:
        if current[key] != reference[key]:
            raise ValueError('Locked v11 configuration changed: '+key)


def process_preflight():
    command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|yolo' } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['pwsh','-NoProfile','-Command',command], text=True).strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes,dict):
        processes = [processes]
    others = [p for p in processes if p['ProcessId'] not in {os.getpid(),os.getppid()}]
    for process in others:
        cmd = (process.get('CommandLine') or '').lower()
        if ('finetune' in cmd or 'train_' in cmd or 'yolo' in cmd or 'run_role_training' in cmd) and ' train' in cmd:
            raise RuntimeError('Another training process is running: '+str(process['ProcessId']))
    gpu = subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv'],text=True).strip()
    return {'observed_at_utc':datetime.now(timezone.utc).isoformat(), 'other_python_yolo_processes':others,
            'other_training_detected':False,'nvidia_smi':gpu}


def verify_inputs(root):
    pp = root/PROTOCOL
    p = json.loads(pp.read_text())
    summary = json.loads((root/'docs/fixtures/role_dataset_merge_summary_v14.json').read_text())
    if digest(pp) != summary['protocol_sha256']:
        raise ValueError('Published protocol changed')
    reference = json.loads(checked(root,p['reference_training_protocol'],p['reference_training_protocol_sha256']).read_text())
    same_configuration(p,reference)
    source = root/p['dataset']
    checked(source,'manifest.json',summary['manifest_sha256'])
    manifest = verify_dataset(root,source,pp)
    validate_sampling(root,p,manifest)
    for spec in p['models']+list(p['comparison_references'].values()):
        checked(root,spec['path'],spec['sha256'])
    old_dir = root/reference['dataset']
    old = verify_dataset(root,old_dir,root/p['reference_training_protocol'])
    if protected_rows(manifest) != protected_rows(old):
        raise ValueError('Validation/test differ from v11')
    for spec in p['merge_releases']:
        directory = root/spec['directory']
        release = json.loads(checked(directory,'manifest.json',spec['manifest_sha256']).read_text())
        checked(root,spec['packet'],spec['packet_sha256'])
        for row in release['files']:
            for kind in ['image','label']:
                checked(directory,row[kind],row[kind+'_sha256'])
    return p,manifest,source


def lock_plan(root):
    p,m,source = verify_inputs(root)
    plan_path = root/PLAN
    destination = root/RUN/'dataset'
    if plan_path.exists() or destination.exists() or (root/RUN/'small').exists():
        raise ValueError('Plan and training artifacts must be new')
    preflight = process_preflight()
    old_args = root/'data/processed/role_sources_training_v11/small/training/args.yaml'
    destination.mkdir(parents=True)
    for row in m['files']:
        for kind in ['image','label']:
            target = destination/row[kind]
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(checked(source,row[kind],row[kind+'_sha256']),target)
    shutil.copyfile(source/'manifest.json',destination/'manifest.json')
    (destination/'data.yaml').write_text(yaml_text(destination))
    verify_dataset(root,destination,root/PROTOCOL)
    plan = {'kind':'role_sources_training_plan_v14','locked_at_utc':datetime.now(timezone.utc).isoformat(),
            'protocol':PROTOCOL,'protocol_sha256':digest(root/PROTOCOL),
            'manifest_sha256':digest(destination/'manifest.json'),
            'parent_sampling_sha256':p['parent_sampling_sha256'],
            'source_dataset':p['dataset'],'training_dataset':destination.relative_to(root).as_posix(),
            'run':RUN+'/small','comparison_output':RUN+'/comparison',
            'images':m['images'],'sampling_lock':p['sampling_lock'],
            'training_configuration':{k:p[k] for k in TRAIN_KEYS},
            'reference_args':old_args.relative_to(root).as_posix(),'reference_args_sha256':digest(old_args),
            'permitted_actual_arg_differences':['data','project','save_dir'],
            'preflight':preflight,'training_started':False,'configurations':1,
            'evaluation_scope':{'models':['v6','v11','v14'],'splits':['val','test'],'sizes':[640,1280],
                                'validation_before_known_test':True,'match128057_inference':False,
                                'known_test_ap':True,'fp32':True,'cross_role_dedup':False},
            'authorization':'User requests one20epoch fresh small run and evaluation; supersedes preparation-only scope. No source diagnostic inference.'}
    write_json(plan_path,plan)
    return plan


def load_plan(root):
    plan = json.loads((root/PLAN).read_text())
    pretrain_path = root/RUN/'pretrain-check.json'
    if pretrain_path.exists() and json.loads(pretrain_path.read_text())['plan_sha256'] != digest(root/PLAN):
        raise ValueError('Plan changed since training preflight')
    p,m,source = verify_inputs(root)
    if digest(root/PROTOCOL) != plan['protocol_sha256'] or digest(source/'manifest.json') != plan['manifest_sha256']:
        raise ValueError('Plan protocol/manifest mismatch')
    if plan['training_configuration'] != {k:p[k] for k in TRAIN_KEYS} or plan['parent_sampling_sha256'] != p['parent_sampling_sha256']:
        raise ValueError('Plan configuration/sampling mismatch')
    dataset = root/plan['training_dataset']
    checked(dataset,'manifest.json',plan['manifest_sha256'])
    snapshot = verify_dataset(root,dataset,root/PROTOCOL)
    validate_sampling(root,p,snapshot)
    checked(root,plan['reference_args'],plan['reference_args_sha256'])
    return plan,p,snapshot,dataset


def actual_configuration(root,plan):
    import yaml
    old = yaml.safe_load(checked(root,plan['reference_args'],plan['reference_args_sha256']).read_text())
    actual_path = root/plan['run']/'training/args.yaml'
    actual = yaml.safe_load(actual_path.read_text())
    differences = {k:{'v11':old.get(k),'v14':actual.get(k)} for k in set(old)|set(actual) if old.get(k)!=actual.get(k)}
    if set(differences)-set(plan['permitted_actual_arg_differences']):
        raise ValueError('Actual training args differ from v11: '+str(differences))
    return {'args_sha256':digest(actual_path),'only_allowed_differences':True,'differences':differences,'actual_args':actual}


def train(root):
    plan,p,m,dataset = load_plan(root)
    preflight = process_preflight()
    (root/RUN).mkdir(parents=True,exist_ok=True)
    write_json(root/RUN/'pretrain-check.json',{'plan_sha256':digest(root/PLAN),'preflight':preflight})
    status = train_one(root,dataset,root/PROTOCOL,root/plan['run'],'small')
    actual = actual_configuration(root,plan)
    load_plan(root)
    write_json(root/RUN/'actual-configuration.json',actual)
    return status


def evaluate_models(paths,dataset,manifest,protocol,output,torch,plan_hash):
    """Only supplied val/test rows; freeze gate before the first test inference."""
    if set(paths) != {'v6','v11','v14'}:
        raise ValueError('Exactly v6/v11/v14 required')
    if set(r['split'] for r in manifest['files'])-{'train','val','test'} or any(str(r.get('match_id'))=='128057' for r in manifest['files']):
        raise ValueError('Unpermitted evaluation source')
    results = {name:{} for name in paths}
    for name,path in paths.items():
        for size in protocol['evaluation_lock']['sizes']:
            results[name][f'validation_ap_{size}'] = evaluate(path,dataset,{**protocol,'evaluation_image_size':size},output,'val',f'{name}_val_ap{size}')
            results[name][f'validation_{size}'] = fixed_confidence(path,dataset,manifest,'val',.25,size)
        gc.collect();torch.cuda.empty_cache()
        write_json(output/'validation-progress.json',results)
    decision = validation_choice(results['v6']['validation_ap_640'],results['v14']['validation_ap_640'],protocol['validation_gate'])
    decision.update(candidate_is='v14',reference_is='v6',gate_resolution=640)
    write_json(output/'validation-before-test.json',{'models':results,'decision':decision,'plan_sha256':plan_hash,
               'weights_sha256':{k:digest(v) for k,v in paths.items()},'match128057_inference':False})
    frozen_hash = digest(output/'validation-before-test.json')
    for name,path in paths.items():
        for size in protocol['evaluation_lock']['sizes']:
            results[name][f'known_test_ap_{size}'] = evaluate(path,dataset,{**protocol,'evaluation_image_size':size},output,'test',f'{name}_test_ap{size}')
            results[name][f'known_test_{size}'] = fixed_confidence(path,dataset,manifest,'test',.25,size)
        gc.collect();torch.cuda.empty_cache()
    return results,decision,frozen_hash


def compare(root):
    plan,p,m,dataset = load_plan(root)
    status = json.loads((root/plan['run']/'status.json').read_text())
    if status['status']!='complete' or status['protocol_sha256']!=plan['protocol_sha256'] or status['manifest_sha256']!=plan['manifest_sha256']:
        raise ValueError('Incomplete/stale training')
    specs = comparison_specs(p,status,'v14')
    paths = {k:checked(root,v['path'],v['sha256']) for k,v in specs.items()}
    actual = actual_configuration(root,plan)
    output = root/plan['comparison_output']
    output.mkdir(parents=True,exist_ok=False)
    torch = setup(root)
    with (output/'evaluation.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        models,decision,frozen_hash = evaluate_models(paths,dataset,m,p,output,torch,digest(root/PLAN))
    load_plan(root)
    for name,spec in specs.items():
        checked(root,spec['path'],spec['sha256'])
    result = {'kind':'role_sources_training_result_v14','plan_sha256':digest(root/PLAN),
              'protocol_sha256':plan['protocol_sha256'],'manifest_sha256':plan['manifest_sha256'],
              'training':status,'actual_configuration':actual,'models':models,'weights':specs,
              'selection_vs_v6':decision,'validation_before_test_sha256':frozen_hash,
              'match128057_inference':False,'old_test_previously_inspected':True,
              'known_regression_test_opened':True,
              'pipeline_promoted':False,'independently_validated':False,'sampling':p['sampling_lock'],
              'evaluation':p['evaluation_lock'],'evaluation_scope':plan['evaluation_scope'],
              'scope':'One fresh COCO11s seed,20epoch. Data-only addition with frozen parent sampling. Not a causal test or independent label acceptance.'}
    write_json(output/'result.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','train','compare'])
    action=parser.parse_args().action
    root=Path(__file__).resolve().parents[2]
    result={'plan':lock_plan,'train':train,'compare':compare}[action](root)
    print(json.dumps(result.get('selection_vs_v6',result),indent=2))
