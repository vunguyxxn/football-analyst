"""Verify and export manually reviewed train-only sources; never train or infer."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from backend.cv.balance_role_dataset import crop_labels, protected_rows
from backend.cv.curate_role_counterexamples import duplicate_hits, git_blob_sha, image_feature, overlaps
from backend.cv.evaluate_role_detector import checked, digest, iou
from backend.cv.prepare_role_dataset import NAMES
from backend.cv.validate_referee_annotations import box_inside


def reviewed_regions(source, label_text):
    """Account for every source box; an active actor cannot be silently cropped out."""
    if source['split'] != 'train' or source['review_status'] != 'agent_reviewed':
        raise ValueError('Only reviewed train sources allowed')
    lines = label_text.splitlines()
    decisions = source['decisions']
    if [d['source_index'] for d in decisions] != list(range(len(lines))):
        raise ValueError('Incomplete source annotation ledger')
    for line, d in zip(lines, decisions):
        cls, x, y, w, h = map(float, line.split())
        expected = [(x-w/2)*source['width'], (y-h/2)*source['height'],
                    (x+w/2)*source['width'], (y+h/2)*source['height']]
        if d['source_class'] != cls or any(abs(a-b) > 1e-6 for a, b in zip(expected, d['xyxy'])) or len(d['xyxy']) != 4:
            raise ValueError('Source geometry/class changed')
        box_inside(d['xyxy'], [0, 0, source['width'], source['height']])
        if not d['reason'] or d['action'] not in {'ball_out_of_scope', 'discard', 'target', 'outside_review'}:
            raise ValueError('Unexplained annotation decision')
        if cls == 0:
            if d['action'] != 'ball_out_of_scope':
                raise ValueError('Ball outside three-role scope')
        elif cls not in {1, 2} or d['action'] == 'ball_out_of_scope':
            raise ValueError('Unknown source class')
        if d['action'] == 'target':
            allowed = {'player', 'goalkeeper'} if cls == 1 else {'referee'}
            if d.get('role') not in allowed:
                raise ValueError('Invalid manual role mapping')
    regions = []
    for r in source['regions']:
        roi = r['roi']
        if r['coverage_reviewed'] is not True or any(type(v) is not int for v in roi):
            raise ValueError('Unreviewed or noninteger ROI')
        box_inside(roi, [0, 0, source['width'], source['height']])
        if any(overlaps(roi, box) for box in source['uncertain_boxes']):
            raise ValueError('Uncertain actor cannot become background')
        objects = []
        for d in decisions:
            if not overlaps(roi, d['xyxy']) or d['action'] in {'discard', 'ball_out_of_scope'}:
                continue
            if d['action'] != 'target':
                raise ValueError('Unreviewed source actor intersects ROI')
            box_inside(d['xyxy'], roi)  # Reject partial target cuts, do not silently drop them.
            objects.append({'id': str(d['source_index']), 'role': d['role'], 'xyxy': d['xyxy']})
        if type(r['negative']) is not bool or r['negative'] != (not objects):
            raise ValueError('Negative ROI contains active role target or positive is empty')
        if r['negative'] and not r['background_types']:
            raise ValueError('Negative ROI needs reviewed background evidence')
        for i, obj in enumerate(objects):
            if any(iou(obj['xyxy'], other['xyxy']) > .9 for other in objects[i+1:]):
                raise ValueError('Duplicate actor annotation')
        regions.append({**r, 'objects': objects, 'labels': crop_labels({'roi': roi, 'objects': objects})})
    return regions


def pixel_hash(image):
    return hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()


def prepare(root, packet_path, output):
    import cv2
    import numpy as np
    root = root.resolve()
    if output.exists() or not output.resolve().is_relative_to(root):
        raise ValueError('Output must be a new workspace directory')
    packet = json.loads(packet_path.read_text(encoding='utf-8'))
    release_kinds = {'reviewed_role_source_release_v12': 'role_source_release_v12',
                     'reviewed_role_source_release_v13': 'role_source_release_v13'}
    if packet['kind'] not in release_kinds or any(packet[k] is not False for k in
            ['independently_validated', 'training_performed', 'runtime_changed', 'role_detector_used_for_selection']):
        raise ValueError('Unsupported release or inference/training claim')
    provider = packet['provider']
    if provider['license'] != 'CC-BY-4.0' or len(provider['revision']) != 40:
        raise ValueError('Unpinned provider/license')
    checked(root, provider['license_path'], provider['license_sha256'])
    groups = json.loads(checked(root, packet['source_groups'], packet['source_groups_sha256']).read_text())
    if groups['revision'] != provider['revision'] or groups['locked_before_role_detector_inference'] is not True:
        raise ValueError('Unlocked source groups')
    sources = packet['sources']
    locked = {s['id']: s for s in groups['sources']}
    if len(locked) != len(sources) or {s['id'] for s in sources} != set(locked):
        raise ValueError('Source registry mismatch')
    ids = [r['id'] for s in sources for r in s['regions']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate ROI identity')
    base_dir = root/packet['base_dataset']
    base_path = checked(base_dir, 'manifest.json', packet['base_manifest_sha256'])
    base = json.loads(base_path.read_text())
    protocol = json.loads(checked(root, packet['base_protocol'], packet['base_protocol_sha256']).read_text())
    references = [(base_dir, row) for row in base['files']]
    for release in protocol['source_releases'] + packet.get('additional_references', []):
        directory = root/release['directory']
        manifest = json.loads(checked(directory, 'manifest.json', release['manifest_sha256']).read_text())
        references.extend((directory, row) for row in manifest['files'])
    seen, pixels, features = set(), set(), []
    # Includes every split and source-heldout ROIs, without running a detector.
    for directory, row in references:
        path = checked(directory, row['image'], row['image_sha256'])
        checked(directory, row['label'], row['label_sha256'])
        if row['image_sha256'] in seen:
            continue
        seen.add(row['image_sha256'])
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError('Unreadable reference image')
        pixels.add(pixel_hash(image))
        features.append({'image': path.relative_to(root).as_posix(), **image_feature(image)})
    reference_count = len(seen)
    additions, native_hashes, primaries = [], set(), []
    protected_families = {r['family'] for r in base['files']}
    for source in sources:
        if {k: source[k] for k in locked[source['id']]} != locked[source['id']] or source['scene_family'] in protected_families:
            raise ValueError('Source lock/protected family changed')
        ip = checked(root, source['path'], source['sha256'])
        lp = checked(root, source['label_path'], source['label_sha256'])
        if git_blob_sha(ip.read_bytes()) != source['git_blob_sha'] or git_blob_sha(lp.read_bytes()) != source['label_git_blob_sha']:
            raise ValueError('Pinned source Git blob mismatch')
        image = cv2.imread(str(ip))
        if image is None or image.shape[:2] != (source['height'], source['width']):
            raise ValueError('Source image dimensions changed')
        native = pixel_hash(image)
        if native in native_hashes or native in pixels or duplicate_hits(image_feature(image), features):
            raise ValueError('Duplicate native source')
        native_hashes.add(native)
        regions = reviewed_regions(source, lp.read_text())
        for region in regions:
            a, b, c, d = region['roi']
            patch = image[b:d, a:c]
            pixel = pixel_hash(patch)
            if pixel in pixels or duplicate_hits(image_feature(patch), features):
                raise ValueError('Duplicate reviewed ROI')
            # Within-parent overlap is declared; cross-parent duplicate candidates are rejected.
            additions.append((source, region, cv2.imencode('.png', patch)[1].tobytes(), pixel))
        for obs in [o for o in packet['primary_observations'] if o['source_id'] == source['id']]:
            region = next(r for r in regions if r['id'] == obs['region_id'])
            obj = next(o for o in region['objects'] if int(o['id']) == obs['source_index'])
            if (obj['role'] == 'goalkeeper' and obs['pose'] not in {'upright', 'upright_moving'}) or (obs['location'] == 'far_touchline' and obj['role'] != 'referee'):
                raise ValueError('Primary pose/role mismatch')
            a, b, c, d = region['roi']
            primaries.append({**obs, 'role': obj['role'], 'height_at_640': (obj['xyxy'][3]-obj['xyxy'][1])*640/max(c-a,d-b), 'scene_family': source['scene_family']})
        # Add this parent's native and crops only AFTER its correlated ROIs are checked.
        for candidate in [image]+[image[r['roi'][1]:r['roi'][3],r['roi'][0]:r['roi'][2]] for r in regions]:
            pixels.add(pixel_hash(candidate))
            features.append({'image': source['id'], **image_feature(candidate)})
    if {o['source_id'] for o in packet['primary_observations']} - {s['id'] for s in sources}:
        raise ValueError('Unknown primary source')
    files, counts = [], Counter()
    output.mkdir(parents=True)
    for source, region, encoded, pixel in additions:
        stem = region['id']
        ip, lp = f'images/train/{stem}.png', f'labels/train/{stem}.txt'
        for path in [ip, lp]:
            (output/path).parent.mkdir(parents=True, exist_ok=True)
        (output/ip).write_bytes(encoded)
        (output/lp).write_text(region['labels'], encoding='utf-8', newline='\n')
        cc = Counter(o['role'] for o in region['objects'])
        counts.update(cc)
        files.append({'image': ip, 'label': lp, 'image_sha256': digest(output/ip), 'label_sha256': digest(output/lp),
                      'pixel_sha256': pixel, 'split': 'train', 'family': source['scene_family'], 'parent': source['id'],
                      'roi': region['roi'], 'negative': region['negative'], 'class_counts': dict(cc)})
        overlay = cv2.imdecode(np.frombuffer(encoded, dtype='uint8'), cv2.IMREAD_COLOR)
        a, b, _, _ = region['roi']
        for obj in region['objects']:
            x1,y1,x2,y2 = [round(v) for v in obj['xyxy']]
            cv2.rectangle(overlay,(x1-a,y1-b),(x2-a,y2-b),(0,255,255),2)
            cv2.putText(overlay,obj['id']+':'+obj['role'],(x1-a,max(15,y1-b-4)),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,255,255),1)
        (output/'review').mkdir(exist_ok=True)
        cv2.imwrite(str(output/'review'/f'{stem}.jpg'),overlay)
    # Recheck every frozen image and label after export; no base write is permitted.
    checked(base_dir, 'manifest.json', packet['base_manifest_sha256'])
    for row in base['files']:
        for kind in ['image', 'label']:
            checked(base_dir, row[kind], row[kind+'_sha256'])
    result = {'kind': release_kinds[packet['kind']], 'packet_sha256': digest(packet_path), 'names': NAMES,
              'training_performed': False, 'runtime_changed': False, 'independently_validated': False,
              'prior_unique_images_screened': reference_count, 'protected_rows_sha256': hashlib.sha256(json.dumps(protected_rows(base)).encode()).hexdigest(),
              'parents': len(sources), 'scene_groups': len({s['scene_family'] for s in sources}),
              'positive_rois': sum(not f['negative'] for f in files), 'negative_rois': sum(f['negative'] for f in files),
              'class_counts': dict(counts), 'primary_observations': primaries, 'files': files,
              'scope': packet['sampling'], 'scene_review': packet['scene_review']}
    (output/'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    (output/'ATTRIBUTION.txt').write_text(provider['attribution']+'\n'+provider['license_url']+'\nChanges additionally: corrected false role boxes, background-only ROI extraction.\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', default='docs/fixtures/role_sources_review_v12.json')
    parser.add_argument('--output', default='data/processed/role_source_release_v12')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = prepare(root, root/args.packet, root/args.output)
    print(json.dumps({k:v for k,v in result.items() if k != 'files'},ensure_ascii=False,indent=2))
