"""Val1280-only v10/v11 keeper FP and referee FN audit; frozen scoring."""
from collections import Counter
import json
from pathlib import Path

from backend.cv.audit_role_regressions import explain, raw_evidence, raw_head, transition
from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest, iou, match
from backend.cv.finetune_roles import setup
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def keeper_false_positives(labels, predictions, paired):
    """Include misclassified GT and unmatched predictions, just like operating_metrics."""
    assigned = {p['prediction']['id']: p for p in paired if p['prediction'] is not None}
    rows = []
    for pred in predictions:
        if pred['role'] != 'goalkeeper':
            continue
        target = assigned.get(pred['id'])
        if target and target['role'] == 'goalkeeper':
            continue
        overlaps = [{**label, 'iou': iou(label['xyxy'], pred['xyxy']),
                     'assigned_prediction': paired[index]['prediction']}
                    for index, label in enumerate(labels) if iou(label['xyxy'], pred['xyxy']) >= .5]
        rows.append({'prediction': pred, 'xyxy': pred['xyxy'],
                     'assigned_label': {k: target[k] for k in ['id', 'role', 'xyxy']} if target else None,
                     'overlapping_labels': overlaps,
                     'mechanism': 'matched_wrong_role' if target else
                     'unmatched_gt_assigned_elsewhere' if overlaps else 'unmatched_no_gt_iou50',
                     'coincident_predictions': [p for p in predictions if p['id'] != pred['id'] and iou(p['xyxy'], pred['xyxy']) >= .5]})
    return rows


def fp_transitions(before, after):
    """Spatial FP association, not identity tracking or simple subtraction of counts."""
    pairs = match([{'id': i, 'role': 'goalkeeper', 'xyxy': row['xyxy']} for i, row in enumerate(before)],
                  [{'id': i, 'role': 'goalkeeper', 'xyxy': row['xyxy']} for i, row in enumerate(after)], box_iou=.5)
    by_after = {p['prediction']['id']: p['id'] for p in pairs if p['prediction'] is not None}
    return [{'transition': 'retained_fp' if i in by_after else 'new_fp',
             'before_fp_index': by_after.get(i)} for i in range(len(after))], len(before)-len(by_after)


def validate_review(audit, review):
    """A visual classification cannot silently drop errors or rewrite scoring evidence."""
    if any(review[k] is not False for k in ['training_performed', 'labels_changed', 'independently_validated', 'test_inference_performed']):
        raise ValueError('Unsupported review claim')
    if (review['size'], review['confidence'], review['nms_iou'], review['matching_iou']) != (1280, .25, .7, .5):
        raise ValueError('Review thresholds changed')
    if review['manifest_sha256'] != audit['manifest_sha256'] or review['weights'] != audit['weights']:
        raise ValueError('Review source binding changed')
    for original_key, reviewed_key in [('keeper_fp_rows', 'keeper_predictions'), ('referee_fn_rows', 'referee_labels')]:
        originals = {r['review_id']: r for r in audit[original_key]}
        rows = review[reviewed_key]
        if len(rows) != len(originals) or {r['review_id'] for r in rows} != set(originals):
            raise ValueError('Incomplete or duplicate review coverage')
        evidence = ['image', 'image_sha256', 'label_sha256', 'xyxy', 'transition', 'height_at_640']
        evidence += ['prediction', 'mechanism', 'assigned_label'] if original_key == 'keeper_fp_rows' else ['label_id', 'v10', 'v11', 'diagnostic', 'raw_v11']
        for row in rows:
            if row['review_status'] != 'agent_reviewed' or any(row[k] != originals[row['review_id']][k] for k in evidence):
                raise ValueError('Frozen review evidence changed')
    return {'keeper_rows': len(review['keeper_predictions']), 'referee_rows': len(review['referee_labels'])}


def export_review(dataset, output, keeper_rows, ref_rows):
    import cv2
    import numpy as np
    for kind, rows in [('keeper', keeper_rows), ('referee', ref_rows)]:
        tiles = []
        for index, row in enumerate(rows):
            row['review_id'] = f'{kind}-{index}'
            image = cv2.imread(str(dataset/row['image']))
            h, w = image.shape[:2]
            a, b, c, d = map(int, row['xyxy'])
            x, y = max(0, a-110), max(0, b-110)
            patch = image[y:min(h, d+110), x:min(w, c+110)].copy()
            cv2.rectangle(patch, (a-x, b-y), (c-x, d-y), (0, 255, 255), 1)
            scale = min(295/patch.shape[1], 205/patch.shape[0])
            patch = cv2.resize(patch, None, fx=scale, fy=scale)
            tile = np.full((260, 300, 3), 25, np.uint8)
            tile[25:25+patch.shape[0], :patch.shape[1]] = patch
            cv2.putText(tile, row['review_id'], (3, 18), 0, .5, (255, 255, 255), 1)
            status = row.get('transition', '')
            cv2.putText(tile, status+' h640='+f'{row["height_at_640"]:.1f}', (3, 251), 0, .44, (255, 255, 255), 1)
            cv2.imwrite(str(output/(row['review_id']+'.jpg')), tile)
            tiles.append(tile)
        for start in range(0, len(tiles), 20):
            group = tiles[start:start+20]
            group += [np.zeros((260, 300, 3), np.uint8)]*(20-len(group))
            cv2.imwrite(str(output/f'{kind}-sheet-{start//20}.jpg'), np.vstack([np.hstack(group[i:i+4]) for i in range(0, 20, 4)]))
    images = list(dict.fromkeys(row['image'] for row in keeper_rows+ref_rows))
    for index, name in enumerate(images):
        image = cv2.imread(str(dataset/name))
        for row in keeper_rows+ref_rows:
            if row['image'] != name:
                continue
            row['context_id'] = index
            a, b, c, d = map(int, row['xyxy'])
            color = (0, 0, 255) if row['review_id'].startswith('keeper') else (0, 255, 0)
            cv2.rectangle(image, (a, b), (c, d), color, 1)
            cv2.putText(image, row['review_id'], (a, max(15, b-4)), 0, .45, color, 1)
        cv2.imwrite(str(output/f'context-{index}.jpg'), image)


def main(root):
    import cv2
    torch = setup(root)
    from ultralytics import YOLO
    pp = root/'docs/fixtures/role_sources_training_protocol_v11.json'
    rp = root/'docs/fixtures/role_sources_training_result_v11.json'
    protocol, frozen = json.loads(pp.read_text()), json.loads(rp.read_text())
    if digest(pp) != frozen['protocol_sha256']:
        raise ValueError('Frozen protocol changed')
    dataset = root/protocol['dataset']
    checked(dataset, 'manifest.json', frozen['manifest_sha256'])
    manifest = verify_dataset(root, dataset, pp)
    specs = {'v10': protocol['comparison_references']['v10'],
             'v11': {'path': frozen['training']['best_weights'], 'sha256': frozen['training']['best_weights_sha256']}}
    paths = {key: checked(root, spec['path'], spec['sha256']) for key, spec in specs.items()}
    models = {key: YOLO(str(path)) for key, path in paths.items()}
    if any(list(model.names.values()) != NAMES for model in models.values()):
        raise ValueError('Role IDs changed')
    output = root/'data/processed/role_error_audit_v11'
    output.mkdir(exist_ok=False)
    totals = {key: [Counter(), Counter()] for key in models}
    keeper_rows, ref_rows, refs_all, frames = [], [], [], []
    resolved_fp, previous_fp = 0, 0
    for item in manifest['files']:
        if item['split'] != 'val':
            continue
        image = cv2.imread(str(dataset/item['image']))
        h, w = image.shape[:2]
        labels = []
        for index, line in enumerate((dataset/item['label']).read_text().splitlines()):
            cls, x, y, bw, bh = map(float, line.split())
            labels.append({'id': index, 'role': NAMES[int(cls)],
                           'xyxy': [(x-bw/2)*w, (y-bh/2)*h, (x+bw/2)*w, (y+bh/2)*h]})
        predictions, paired, fps = {}, {}, {}
        for name, model in models.items():
            pred = model.predict(image, imgsz=1280, conf=.25, iou=.7, max_det=300, device=0, half=False, verbose=False)[0]
            predictions[name] = [{'id': i, 'role': NAMES[int(role)], 'xyxy': box, 'confidence': score}
                                for i, (box, role, score) in enumerate(zip(pred.boxes.xyxy.cpu().tolist(), pred.boxes.cls.cpu().tolist(), pred.boxes.conf.cpu().tolist()))]
            paired[name] = match(labels, predictions[name], box_iou=.5)
            confusion, extras = frame_confusion(labels, predictions[name])
            totals[name][0].update(confusion); totals[name][1].update(extras)
            fps[name] = keeper_false_positives(labels, predictions[name], paired[name])
        common = {key: item[key] for key in ['image', 'image_sha256', 'label_sha256']}
        changes, resolved = fp_transitions(fps['v10'], fps['v11'])
        resolved_fp += resolved; previous_fp += len(fps['v10'])
        for row, change in zip(fps['v11'], changes):
            before = fps['v10'][change['before_fp_index']] if change['before_fp_index'] is not None else None
            keeper_rows.append({**common, **row, **change, 'before_fp': before,
                                'height_at_640': (row['xyxy'][3]-row['xyxy'][1])*640/max(w, h)})
        pending = []
        for index, label in enumerate(labels):
            if label['role'] != 'referee':
                continue
            before, after = (paired[name][index]['prediction'] for name in ['v10', 'v11'])
            row = {**common, 'label_id': index, 'xyxy': label['xyxy'], 'v10': before, 'v11': after,
                   'transition': transition('referee', before, after),
                   'height_at_640': (label['xyxy'][3]-label['xyxy'][1])*640/max(w, h)}
            refs_all.append(row)
            if after is None or after['role'] != 'referee':
                pending.append((row, label)); ref_rows.append(row)
        if pending:
            head = raw_head(models['v11'], image, torch)
            for row, label in pending:
                row['raw_v11'] = raw_evidence(label, head)
                row['diagnostic'] = explain(label, row['v11'], predictions['v11'], row['raw_v11'])
                row['correct_role_candidates'] = [p for p in predictions['v11'] if p['role'] == 'referee' and iou(label['xyxy'], p['xyxy']) >= .5]
        frames.append({**common, 'labels': labels, 'predictions': predictions})
    reproduced = {name: operating_metrics(*counts) for name, counts in totals.items()}
    for name, actual in reproduced.items():
        expected = frozen['models'][name]['validation_1280']
        if any(actual[key] != expected[key] for key in ['classes', 'confusion', 'unmatched_predictions']):
            raise ValueError('All-class val1280 replay differs')
    if len(keeper_rows) != reproduced['v11']['classes']['goalkeeper']['fp'] or len(ref_rows) != reproduced['v11']['classes']['referee']['fn']:
        raise ValueError('Error rows do not reproduce scoring')
    export_review(dataset, output, keeper_rows, ref_rows)
    summary = {'keeper_fp': len(keeper_rows), 'previous_keeper_fp': previous_fp, 'resolved_old_fp': resolved_fp,
               'keeper_fp_transitions': dict(Counter(row['transition'] for row in keeper_rows)),
               'keeper_fp_mechanisms': dict(Counter(row['mechanism'] for row in keeper_rows)),
               'referee_labels': len(refs_all), 'referee_transitions': dict(Counter(row['transition'] for row in refs_all)),
               'referee_fn': len(ref_rows), 'referee_fn_diagnostics': dict(Counter(row['diagnostic'] for row in ref_rows))}
    verify_dataset(root, dataset, pp)
    for name, path in paths.items():
        checked(root, specs[name]['path'], specs[name]['sha256'])
    result = {'summary': summary, 'keeper_fp_rows': keeper_rows, 'referee_fn_rows': ref_rows, 'all_referee_rows': refs_all,
              'reproduced_all_class_validation': reproduced, 'protocol_sha256': digest(pp),
              'comparison_result_sha256': digest(rp), 'manifest_sha256': frozen['manifest_sha256'], 'weights': specs,
              'size': 1280, 'confidence': .25, 'nms_iou': .7, 'matching_iou': .5,
              'training_performed': False, 'labels_changed': False, 'test_opened': False,
              'scope': 'Val only. FP means frozen-label scoring, not independently verified false person. Spatial FP transitions are not identities. Raw scores explain inference stage only, not causal training effects.'}
    (output/'predictions.json').write_text(json.dumps(frames, indent=2)+'\n')
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main(Path(__file__).resolve().parents[2])
