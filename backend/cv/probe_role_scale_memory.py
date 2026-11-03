"""One disposable loss/backward/AdamW step at maximum shape; no weights saved."""
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.finetune_roles import setup


def main(root):
    import cv2
    torch=setup(root)
    from ultralytics import YOLO
    from ultralytics.cfg import DEFAULT_CFG_DICT
    p=json.loads((root/'docs/fixtures/role_scale_multi_protocol_v7.json').read_text())
    spec=p['models'][0];weights=checked(root,spec['path'],spec['sha256'])
    dataset=root/'data/processed/role_scale_v7/multi_dataset'
    manifest=json.loads((dataset/'manifest.json').read_text());row=next(r for r in manifest['files'] if r['split']=='train' and r.get('sampling_origin')=='base_full_frame')
    torch.manual_seed(p['seed'])
    model=YOLO(str(weights)).model.to('cuda').float().train()
    for name,parameter in model.named_parameters():
        parameter.requires_grad_('.dfl.' not in name)
    model.args=SimpleNamespace(**{**DEFAULT_CFG_DICT,**vars(model.args)}) if not isinstance(model.args,dict) else SimpleNamespace(**{**DEFAULT_CFG_DICT,**model.args})
    image=cv2.imread(str(checked(dataset,row['image'],row['image_sha256'])))
    image=cv2.resize(image,(1344,1344))[:,:,::-1].copy()
    tensor=torch.from_numpy(image).permute(2,0,1).unsqueeze(0).to('cuda').float()/255
    targets=[list(map(float,l.split())) for l in checked(dataset,row['label'],row['label_sha256']).read_text().splitlines()]
    target=torch.tensor(targets,device='cuda')
    batch={'img':tensor,'cls':target[:,0:1],'bboxes':target[:,1:5],'batch_idx':torch.zeros(len(targets),device='cuda')}
    optimizer=torch.optim.AdamW(model.parameters(),lr=p['lr0'])
    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();started=perf_counter()
    loss,_=model.loss(batch)
    if not torch.isfinite(loss).all():raise ValueError('Nonfinite smoke loss')
    loss.sum().backward();optimizer.step();torch.cuda.synchronize()
    result={'kind':'role_scale_memory_probe_v7','shape':[1,3,1344,1344],'precision':'FP32','optimizer':'AdamW',
            'steps':1,'peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,'peak_reserved_mib':torch.cuda.max_memory_reserved()/1024**2,
            'elapsed_s':perf_counter()-started,'finite_loss':True,'weights_saved':False,
            'scope':'Disposable model copy, one square resized training image; no augmentation/validation loader, not full-run memory guarantee. Tensor/reserved stats exclude driver and other processes.'}
    if digest(weights)!=spec['sha256']:raise ValueError('Input weights changed')
    (root/'docs/fixtures/role_scale_memory_probe_v7.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
