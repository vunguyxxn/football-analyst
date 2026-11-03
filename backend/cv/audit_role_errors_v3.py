"""Paired role-blind error audit on frozen validation labels, without training."""
import json
from collections import Counter
from pathlib import Path

from backend.cv.evaluate_role_detector import checked, match
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def main(root):
    import cv2
    from ultralytics import YOLO
    setup(root)
    dataset = root / 'data/processed/role_dataset_v3'
    manifest = verify_dataset(root, dataset, root / 'docs/fixtures/role_training_protocol_v3.json')
    report = json.loads((root / 'docs/fixtures/role_training_result_v3.json').read_text())
    specs = json.loads((root / 'docs/fixtures/role_training_protocol_v3.json').read_text())['models']
    models = {'v1': YOLO(str(checked(root, specs[0]['path'], specs[0]['sha256']))),
              'v3': YOLO(str(checked(root, report['training']['best_weights'], report['training']['best_weights_sha256'])))}
    if any(list(model.names.values()) != NAMES for model in models.values()):
        raise ValueError('Unexpected role mapping')
    output = root / 'data/processed/role_error_audit_v3'
    output.mkdir(exist_ok=False)
    rows = []
    for item in manifest['files']:
        if item['split'] != 'val':
            continue
        image = cv2.imread(str(dataset / item['image']))
        height, width = image.shape[:2]
        labels = []
        for i, line in enumerate((dataset / item['label']).read_text().splitlines()):
            role, x, y, w, h = map(float, line.split())
            labels.append({'id': i, 'role': NAMES[int(role)], 'xyxy': [(x-w/2)*width, (y-h/2)*height, (x+w/2)*width, (y+h/2)*height]})
        paired = {}
        for name, model in models.items():
            pred = model.predict(image, imgsz=640, conf=.25, iou=.7, max_det=300, device=0, verbose=False)[0]
            predictions = [{'role': NAMES[int(role)], 'xyxy': box, 'confidence': score}
                           for box, role, score in zip(pred.boxes.xyxy.cpu().tolist(), pred.boxes.cls.cpu().tolist(), pred.boxes.conf.cpu().tolist())]
            paired[name] = match(labels, predictions, box_iou=.5)
        for i, label in enumerate(labels):
            if label['role'] != 'player':
                continue
            predictions = {n: paired[n][i]['prediction'] for n in models}
            errors = {n: bool(p and p['role'] == 'referee') for n, p in predictions.items()}
            if not any(errors.values()):
                continue
            kind = 'persistent' if all(errors.values()) else ('introduced' if errors['v3'] else 'removed')
            a,b,c,d = label['xyxy']
            rows.append({'image': item['image'], 'label_id': i, 'xyxy': label['xyxy'], 'kind': kind,
                         'height_at_640': (d-b)*640/max(width,height), 'predictions': predictions})
    for name, key in [('v1', 'baseline'), ('v3', 'balanced')]:
        count = sum(bool(r['predictions'][name] and r['predictions'][name]['role'] == 'referee') for r in rows)
        if count != report['models'][key]['validation_fixed_confidence']['player_called_referee']:
            raise ValueError('Audit does not reproduce frozen confusion totals')
    # Deterministic spread across images and transition types; not a random prevalence sample.
    selected = []
    for kind in ['persistent', 'introduced', 'removed']:
        group = sorted([r for r in rows if r['kind'] == kind], key=lambda r: (r['image'],r['label_id']))
        selected.extend(group[int(i*len(group)/min(20,len(group)))] for i in range(min(20,len(group))))
    for index, row in enumerate(selected):
        row['review_id'] = index
        image = cv2.imread(str(dataset / row['image']))
        a,b,c,d = map(int,row['xyxy']); height,width = image.shape[:2]
        patch = image[max(0,b-35):min(height,d+35),max(0,a-35):min(width,c+35)]
        scale = min(190/patch.shape[1],150/patch.shape[0])
        patch = cv2.resize(patch,None,fx=scale,fy=scale)
        import numpy as np
        tile = np.full((210,210,3),35,dtype=np.uint8)
        tile[30:30+patch.shape[0],:patch.shape[1]]=patch
        cv2.putText(tile,f'{index} {row["kind"]}',(4,18),0,.43,(255,255,255),1)
        cv2.putText(tile,f'h640={row["height_at_640"]:.1f}px',(4,198),0,.43,(255,255,255),1)
        cv2.imwrite(str(output / f'crop-{index}.jpg'),tile)
    import numpy as np
    for start in range(0,len(selected),20):
        tiles = [cv2.imread(str(output / f'crop-{i}.jpg')) for i in range(start,min(start+20,len(selected)))]
        tiles += [np.zeros((210,210,3),dtype=np.uint8)]*(20-len(tiles))
        cv2.imwrite(str(output / f'sheet-{start//20}.jpg'),np.vstack([np.hstack(tiles[i:i+5]) for i in range(0,20,5)]))
    summary = {'counts': dict(Counter(r['kind'] for r in rows)), 'selected': selected,
               'size_bins': {kind: dict(Counter('under24' if r['height_at_640']<24 else '24to48' if r['height_at_640']<48 else '48plus' for r in rows if r['kind']==kind)) for kind in ['persistent','introduced','removed']},
               'note': 'Removed means no longer matched as referee; can be player, keeper or missed. Provided validation labels are not independently verified.'}
    (output / 'audit.json').write_text(json.dumps({'summary':summary,'errors':rows},indent=2))
    print(summary['counts'])


if __name__ == '__main__':
    main(Path(__file__).resolve().parents[2])
