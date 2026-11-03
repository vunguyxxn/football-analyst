"""Sparse new-match diagnostic after freezing agent-reviewed heldout annotations."""
import json
from pathlib import Path
from backend.cv.compare_role_models import fixed_confidence
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import setup


def main(root):
    setup(root)
    dataset=root/'data/processed/role_source_release_v8'
    mp=dataset/'manifest.json';manifest=json.loads(mp.read_text())
    for row in manifest['files']:
        for key in ['image','label']:checked(dataset,row[key],row[key+'_sha256'])
    if manifest['locked_match_splits']['128057']!='heldout_review':raise ValueError('Heldout match assignment changed')
    selected={'files':[{**r,'split':'test'} for r in manifest['files'] if r['split']=='heldout_review']}
    output=root/'data/processed/role_sources_diagnostic_v8';output.mkdir(exist_ok=False)
    frozen={'annotation_manifest_sha256':digest(mp),'packet_sha256':manifest['packet_sha256'],
            'image_ids':[r['id'] for r in selected['files']],'sizes':[640,1280],'confidence':.25,
            'nms_iou':.7,'matching_iou':.5,'role_dedup':False}
    (output/'annotations-before-inference.json').write_text(json.dumps(frozen,indent=2))
    specs={}
    specs['v6']=json.loads((root/'docs/fixtures/role_clean_training_result_v6.json').read_text())['training']
    paired=json.loads((root/'docs/fixtures/role_scale_result_v7.json').read_text())['training']
    specs.update({'v7_fixed':paired['fixed'],'v7_multi':paired['multi']})
    results={}
    for name,spec in specs.items():
        weights=checked(root,spec['best_weights'],spec['best_weights_sha256'])
        results[name]={str(size):fixed_confidence(weights,dataset,selected,'test',.25,size) for size in [640,1280]}
        if digest(weights)!=spec['best_weights_sha256']:raise ValueError('Weights changed')
    report={'frozen_inputs':frozen,'results':results,'scope':'Two keyframes of one new match;16player/1keeper/2ref labels assisted by COCO person proposals and agent review. No training or model selection; not full-clip accuracy, tracking accuracy or independent human validation.'}
    (output/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps({name:{size:{role:m['classes'][role]['tp'] for role in ['player','goalkeeper','referee']} for size,m in values.items()} for name,values in results.items()}))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
