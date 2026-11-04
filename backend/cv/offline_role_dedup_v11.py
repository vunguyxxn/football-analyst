"""Locked v11 cross-role suppression experiment at 640/1280; never deploy."""
from collections import Counter
import json
from pathlib import Path
from time import perf_counter

from backend.cv.audit_role_regressions import transition
from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest, match
from backend.cv.finetune_roles import setup
from backend.cv.offline_role_dedup import suppress_cross_role
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def evaluate_frames(frames, expected):
    states = {key: [Counter(), Counter()] for key in ['original', 'deduplicated']}
    transitions = {role: Counter() for role in NAMES}
    changes, events, pairs = [], [], Counter()
    before_count, after_count = 0, 0
    for frame in frames:
        labels, original = frame['labels'], frame['predictions']
        filtered, removed = suppress_cross_role(original, threshold=.7)
        before_count += len(original); after_count += len(filtered)
        for key, predictions in [('original', original), ('deduplicated', filtered)]:
            counts, extras = frame_confusion(labels, predictions)
            states[key][0].update(counts); states[key][1].update(extras)
        before, after = match(labels, original, box_iou=.5), match(labels, filtered, box_iou=.5)
        for first, second in zip(before, after):
            role = first['role']
            kind = transition(role, first['prediction'], second['prediction'])
            transitions[role][kind] += 1
            if kind in {'gained', 'lost'}:
                changes.append({k: frame[k] for k in ['image', 'image_sha256', 'label_sha256']} |
                               {'label_id': first['id'], 'role': role, 'xyxy': first['xyxy'], 'transition': kind,
                                'before': first['prediction'], 'after': second['prediction']})
        for removal in removed:
            loser, winner = (original[removal[key]] for key in ['removed_index', 'winner_index'])
            pairs[loser['role']+'->'+winner['role']] += 1
        if removed:
            events.append({k: frame[k] for k in ['image', 'image_sha256', 'label_sha256']} |
                          {'predictions': original, 'suppressed': removed})
    reports = {key: operating_metrics(*counts) for key, counts in states.items()}
    if len(frames) != expected['frames'] or any(reports['original'][key] != expected[key] for key in
                                               ['classes', 'confusion', 'unmatched_predictions']):
        raise ValueError('Frozen baseline not reproduced for all three classes')
    report = {**reports, 'frames': len(frames), 'transitions': {r: dict(c) for r, c in transitions.items()},
              'suppression_pairs': dict(pairs), 'predictions_before': before_count,
              'predictions_after': after_count, 'removed': before_count-after_count}
    return report, changes, events


def main(root):
    import cv2
    pp = root/'docs/fixtures/offline_role_dedup_protocol_v11.json'
    p = json.loads(pp.read_text())
    if (p['sizes'], p['splits'], p['confidence'], p['nms_iou'], p['cross_role_iou_strictly_greater_than'],
        p['matching_iou'], p['max_det'], p['half']) != ([640, 1280], ['val', 'test'], .25, .7, .7, .5, 300, False):
        raise ValueError('Locked experiment settings changed')
    checked(root, p['policy_source'], p['policy_source_sha256'])
    protocol = checked(root, p['dataset_protocol'], p['dataset_protocol_sha256'])
    dataset = checked(root, p['dataset']+'/manifest.json', p['manifest_sha256']).parent
    manifest = verify_dataset(root, dataset, protocol)
    reference = json.loads(checked(root, p['reference_result'], p['reference_result_sha256']).read_text())
    if reference['manifest_sha256'] != p['manifest_sha256'] or reference['training']['best_weights_sha256'] != p['weights']['sha256']:
        raise ValueError('Reference model/dataset binding changed')
    weights = checked(root, p['weights']['path'], p['weights']['sha256'])
    output = (root/p['output']).resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Output must be a new workspace directory')
    setup(root)
    from ultralytics import YOLO
    model = YOLO(str(weights))
    if list(model.names.values()) != NAMES:
        raise ValueError('Unexpected roles')
    output.mkdir(parents=True)
    (output/'protocol-before-run.json').write_bytes(pp.read_bytes())
    results, changes, events, predictions_export = {}, [], [], []
    started = perf_counter()
    for split in p['splits']:
        results[split] = {}
        for size in p['sizes']:
            frames = []
            for row in manifest['files']:
                if row['split'] != split:
                    continue
                image = cv2.imread(str(dataset/row['image']))
                h, w = image.shape[:2]
                labels = []
                for index, line in enumerate((dataset/row['label']).read_text().splitlines()):
                    cls, x, y, bw, bh = map(float, line.split())
                    labels.append({'id': index, 'role': NAMES[int(cls)],
                                   'xyxy': [(x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]})
                pred = model.predict(image, imgsz=size, conf=.25, iou=.7, max_det=300, device=0, half=False, verbose=False)[0]
                predictions = [{'id': i, 'role': NAMES[int(role)], 'xyxy': box, 'confidence': score}
                               for i, (box, role, score) in enumerate(zip(pred.boxes.xyxy.cpu().tolist(), pred.boxes.cls.cpu().tolist(), pred.boxes.conf.cpu().tolist()))]
                frames.append({k: row[k] for k in ['image', 'image_sha256', 'label_sha256']} |
                              {'labels': labels, 'predictions': predictions})
            expected_key = f'validation_{size}' if split == 'val' else f'known_test_{size}'
            report, changed, suppressed = evaluate_frames(frames, reference['models']['v11'][expected_key])
            results[split][str(size)] = report
            changes.extend({'split': split, 'size': size, **row} for row in changed)
            events.extend({'split': split, 'size': size, **row} for row in suppressed)
            predictions_export.extend({'split': split, 'size': size, **row} for row in frames)
            print(split, size, json.dumps({key: report[key] for key in ['original', 'deduplicated', 'removed', 'transitions']}), flush=True)
            # Validation result is frozen before opening the known regression test.
            if split == 'val':
                (output/'validation-before-test.json').write_text(json.dumps(results['val'], indent=2)+'\n')
    verify_dataset(root, dataset, protocol)
    checked(root, p['weights']['path'], p['weights']['sha256'])
    checked(root, p['policy_source'], p['policy_source_sha256'])
    if digest(pp) != digest(output/'protocol-before-run.json'):
        raise ValueError('Protocol changed while running')
    report = {'kind': 'offline_role_dedup_v11', 'protocol_sha256': digest(pp), 'manifest_sha256': p['manifest_sha256'],
              'weights_sha256': p['weights']['sha256'], 'reference_result_sha256': p['reference_result_sha256'],
              'policy': p['policy'], 'scope': p['scope'], 'sizes': p['sizes'], 'results': results,
              'elapsed_s': perf_counter()-started, 'training_performed': False, 'labels_changed': False,
              'pipeline_promoted': False, 'heldout_inference_performed': False,
              'limitation': 'Known labels and regression sets; no independent accuracy or automatic promotion. Suppression can remove distinct overlapping people. No threshold sweep or AP/gate change.'}
    for name, value in [('result', report), ('label-changes', changes), ('suppression-events', events), ('predictions', predictions_export)]:
        (output/(name+'.json')).write_text(json.dumps(value, indent=2)+'\n')
    return report


if __name__ == '__main__':
    main(Path(__file__).resolve().parents[2])
