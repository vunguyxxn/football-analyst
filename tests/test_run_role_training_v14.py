import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.cv import run_role_training_v14 as runner

ROOT = Path(__file__).resolve().parents[1]


def protocol():
    return json.loads((ROOT/runner.PROTOCOL).read_text())


def test_all_locked_settings_match_v11_and_changes_fail():
    p = protocol()
    old = json.loads((ROOT/p['reference_training_protocol']).read_text())
    runner.same_configuration(p,old)
    for key in ['epochs','batch','amp','seed','multi_scale','evaluation_lock','validation_gate']:
        changed = copy.deepcopy(p)
        changed[key] = 'changed'
        with pytest.raises(ValueError,match=key):
            runner.same_configuration(changed,old)
    plan = json.loads((ROOT/runner.PLAN).read_text())
    assert plan['evaluation_scope']['match128057_inference'] is False
    assert plan['configurations'] == 1
    assert plan['manifest_sha256'] == '36ccf26608d992315715b6fd3b58d37e71d1b9fecd0ec10603834b5e4049933f'


def test_validation_is_frozen_before_every_known_test_call(tmp_path,monkeypatch):
    paths = {}
    for name in ['v6','v11','v14']:
        path = tmp_path/(name+'.pt');path.write_bytes(name.encode());paths[name] = path
    calls = []
    def record(split):
        if split == 'test':
            frozen = json.loads((tmp_path/'validation-before-test.json').read_text())
            assert frozen['decision']['checks']['referee_ap50_gain'] is True
            assert frozen['match128057_inference'] is False
        calls.append(split)
    def ap(path,dataset,p,output,split,name):
        record(split)
        return {'map50_95':.5,'classes':{r:{'map50':.1 if path.stem=='v6' else .3} for r in ['player','goalkeeper','referee']}}
    def operating(path,dataset,manifest,split,confidence,size):
        record(split)
        assert confidence == .25 and size in [640,1280]
        return {'frames':128 if split=='val' else 35}
    monkeypatch.setattr(runner,'evaluate',ap)
    monkeypatch.setattr(runner,'fixed_confidence',operating)
    torch = SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:None))
    results,decision,frozen = runner.evaluate_models(paths,tmp_path,{'files':[]},protocol(),tmp_path,torch,'plan')
    assert calls == ['val']*12+['test']*12
    assert len(results)==3 and frozen and all(decision['checks'].values())


def test_diagnostic_rows_rejected_before_inference(tmp_path):
    paths = {name:tmp_path/(name+'.pt') for name in ['v6','v11','v14']}
    with pytest.raises(ValueError,match='Unpermitted'):
        runner.evaluate_models(paths,tmp_path,{'files':[{'split':'heldout_review','match_id':'128057'}]},protocol(),tmp_path,None,'plan')
    assert not (tmp_path/'validation-before-test.json').exists()


def test_other_training_process_blocks_preflight(monkeypatch):
    monkeypatch.setattr(runner.subprocess,'check_output',lambda *a,**k:json.dumps([{'ProcessId':987654,'Name':'python.exe','CommandLine':'python -m backend.cv.finetune_roles train'}]))
    with pytest.raises(RuntimeError,match='Another training process'):
        runner.process_preflight()


def test_actual_args_allow_only_paths_and_reject_precision_change(tmp_path):
    import yaml
    from backend.cv.evaluate_role_detector import digest
    old = tmp_path/'old.yaml'
    old.write_text(yaml.safe_dump({'data':'old/data.yaml','project':'old','save_dir':'old/training',
                                  'amp':False,'half':False,'epochs':20,'batch':4}))
    directory = tmp_path/'run/training';directory.mkdir(parents=True)
    actual = directory/'args.yaml'
    args = yaml.safe_load(old.read_text())
    args.update(data='new/data.yaml',project='new',save_dir='new/training')
    actual.write_text(yaml.safe_dump(args))
    plan = {'reference_args':'old.yaml','reference_args_sha256':digest(old),'run':'run',
            'permitted_actual_arg_differences':['data','project','save_dir']}
    assert runner.actual_configuration(tmp_path,plan)['only_allowed_differences'] is True
    args['amp'] = True
    actual.write_text(yaml.safe_dump(args))
    with pytest.raises(ValueError,match='Actual training args'):
        runner.actual_configuration(tmp_path,plan)
