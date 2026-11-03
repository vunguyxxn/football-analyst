"""Frozen paired scale experiment: validate both runs before known test readback."""
import contextlib
import gc
import json
from pathlib import Path

from backend.cv.balance_role_dataset import protected_rows
from backend.cv.compare_role_models import fixed_confidence, validation_choice
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import evaluate, setup, write_json
from backend.cv.prepare_role_dataset import verify_dataset


def main(root):
    plan_path=root/'docs/fixtures/role_scale_plan_v7.json'
    plan=json.loads(plan_path.read_text())
    baseline=json.loads((root/'docs/fixtures/role_clean_training_result_v6.json').read_text())
    runs={};datasets={};manifests={};protocols={};weights={}
    for arm,item in plan['arms'].items():
        pp=checked(root,item['protocol'],item['protocol_sha256'])
        dataset=root/item['dataset'];checked(dataset,'manifest.json',item['manifest_sha256'])
        manifest=verify_dataset(root,dataset,pp)
        status=json.loads((root/f'data/processed/role_scale_v7/{arm}_run/status.json').read_text())
        if status['status']!='complete' or status['protocol_sha256']!=digest(pp) or status['manifest_sha256']!=digest(dataset/'manifest.json'):
            raise ValueError('Incomplete or stale paired run')
        weights[arm]=checked(root,status['best_weights'],status['best_weights_sha256'])
        runs[arm]=status;datasets[arm]=dataset;manifests[arm]=manifest;protocols[arm]=json.loads(pp.read_text())
    if manifests['fixed']['files']!=manifests['multi']['files']:
        raise ValueError('Paired datasets differ')
    output=root/'data/processed/role_scale_v7/comparison';output.mkdir(exist_ok=False)
    torch=setup(root);results={arm:{} for arm in runs}
    with (output/'evaluation.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        baseline_spec=protocols['fixed']['comparison_baseline']
        baseline_weights=checked(root,baseline_spec['path'],baseline_spec['sha256'])
        baseline_validation=evaluate(baseline_weights,datasets['fixed'],protocols['fixed'],output,'val','v1_val_ap640_same_batch')
        for arm in runs:
            p=protocols[arm]
            results[arm]['validation_ap640']=evaluate(weights[arm],datasets[arm],p,output,'val',arm+'_val_ap640')
            for size in [640,1280]:
                results[arm][f'validation_{size}']=fixed_confidence(weights[arm],datasets[arm],manifests[arm],'val',.25,size)
            results[arm]['gate_vs_v1']=validation_choice(baseline_validation,results[arm]['validation_ap640'],p['validation_gate'])
            gc.collect();torch.cuda.empty_cache()
        # Freeze complete validation results for BOTH arms before opening known test.
        write_json(output/'validation-before-test.json',{'results':results,'baseline_v1_validation':baseline_validation,'weights_sha256':{a:digest(w) for a,w in weights.items()},'plan_sha256':digest(plan_path)})
        for arm in runs:
            for size in [640,1280]:
                results[arm][f'known_test_{size}']=fixed_confidence(weights[arm],datasets[arm],manifests[arm],'test',.25,size)
            gc.collect();torch.cuda.empty_cache()
    for arm in runs:
        item=plan['arms'][arm]
        after=verify_dataset(root,datasets[arm],checked(root,item['protocol'],item['protocol_sha256']))
        if protected_rows(after)!=protected_rows(manifests[arm]) or digest(weights[arm])!=runs[arm]['best_weights_sha256']:
            raise ValueError('Experiment artifacts changed')
    result={'kind':'paired_role_scale_result_v7','plan_sha256':digest(plan_path),'training':runs,'results':results,
            'reference_v6':baseline['models']['balanced'],'baseline_v1_validation_same_batch':baseline_validation,'pipeline_promoted':False,'test_previously_inspected':True,
            'scope':'Paired fixed896/multi448-1344 warm-start v6, same data/seed/hyperparameters. One seed, no independent validation. Confidence .25, NMS .7, matching IoU .5; no offline role dedup.'}
    write_json(output/'result.json',result)
    print(json.dumps({a:{k:v for k,v in r.items() if k=='gate_vs_v1'} for a,r in results.items()}))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
