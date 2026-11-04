"""Offline, immutable role-label corrections and reviewed wide-context additions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from backend.cv.balance_role_dataset import crop_labels, protected_rows
from backend.cv.curate_role_counterexamples import duplicate_hits, git_blob_sha, image_feature, overlaps
from backend.cv.evaluate_role_detector import checked, digest, iou
from backend.cv.prepare_role_dataset import NAMES, verify_dataset, yaml_text
from backend.cv.validate_referee_annotations import box_inside


def amend(text, change):
    """Change only one class token, preserving every coordinate and line ending."""
    lines = text.splitlines(keepends=True)
    index = change['line_index']
    if type(index) is not int or not 0 <= index < len(lines):
        raise ValueError('Invalid correction index')
    line = lines[index]
    if len(line.split()) != 5 or line.split()[0] != change['from_class']:
        raise ValueError('Unexpected correction class')
    if change['action'] != 'relabel' or change['to_class'] not in {'0', '1', '2'}:
        raise ValueError('Unsupported correction')
    start = len(line)-len(line.lstrip())
    lines[index] = line[:start]+change['to_class']+line[start+len(change['from_class']):]
    return ''.join(lines)


def validate_source(source, locked):
    if source['split'] != 'train' or source['review_status'] != 'agent_reviewed':
        raise ValueError('Only reviewed train sources allowed')
    if {k: source[k] for k in locked} != locked:
        raise ValueError('Locked source identity changed')
    box_inside(source['roi'], [0, 0, source['width'], source['height']])
    if any(type(v) is not int for v in source['roi']):
        raise ValueError('Integer ROI required')
    if any(overlaps(source['roi'], b['xyxy']) for b in source['uncertain_boxes']):
        raise ValueError('Uncertain actor would become background')
    ids = set()
    for obj in source['objects']:
        if obj['id'] in ids or obj['role'] not in NAMES:
            raise ValueError('Duplicate or unsupported role')
        ids.add(obj['id'])
        box_inside(obj['xyxy'], source['roi'])
        # The source merges keepers into player; splitting needs explicit review.
        expected = ['player', 'goalkeeper'] if obj['source_class'] == 1 else ['referee']
        if obj['source_class'] not in {1, 2} or obj['role'] not in expected:
            raise ValueError('Source class mapping mismatch')
    for i, obj in enumerate(source['objects']):
        if any(iou(obj['xyxy'], other['xyxy']) > .9 for other in source['objects'][i+1:]):
            raise ValueError('Duplicate actor annotation')
    primary = next((o for o in source['objects'] if o['id'] == source['primary_id']), None)
    expected_role = 'referee' if source['primary_location'] == 'far_touchline' else 'goalkeeper'
    if primary is None or primary['role'] != expected_role:
        raise ValueError('Primary role mismatch')
    return crop_labels(source)


def clean_rows(base, changes):
    """Quarantine all pixel-identical exposures; never turn a suspect box negative."""
    rows, quarantined, corrected = [], [], []
    for change in changes:
        matches = [r for r in base['files'] if r['image'] == change['image']]
        if len(matches) != 1 or any(matches[0][k] != change[k] for k in
                                   ['image_sha256', 'label_sha256', 'pixel_sha256']):
            raise ValueError('Correction target/hash changed')
        if matches[0]['split'] != 'train' or change['action'] not in {'quarantine', 'relabel'}:
            raise ValueError('Cannot change protected split or unsupported action')
    if len({c['pixel_sha256'] for c in changes}) != len(changes):
        raise ValueError('Conflicting corrections')
    for original in base['files']:
        change = next((c for c in changes if c['pixel_sha256'] == original['pixel_sha256']), None)
        if change and original['split'] != 'train':
            raise ValueError('Correction reaches protected pixels')
        if change and change['action'] == 'quarantine':
            quarantined.append(original['image'])
            continue
        if change:
            # A differently cropped/relabelled exposure needs its own explicit review.
            if original['label_sha256'] != change['label_sha256']:
                raise ValueError('Unreviewed alternate labels for corrected pixels')
            corrected.append(original['image'])
        rows.append((dict(original), change))
    return rows, quarantined, corrected


def prepare(root, protocol_path):
    import cv2
    p = json.loads(protocol_path.read_text())
    if p['new_source_repeats'] != 1 or p['training_started'] is not False:
        raise ValueError('Data-only single-exposure protocol required')
    base_dir = checked(root, p['base_dataset']+'/manifest.json', p['base_manifest_sha256']).parent
    base_protocol = checked(root, p['base_protocol'], p['base_protocol_sha256'])
    base = verify_dataset(root, base_dir, base_protocol)
    packet = json.loads(checked(root, p['annotation_packet'], p['annotation_packet_sha256']).read_text())
    if packet['kind'] != 'reviewed_role_sources_v11' or any(packet[k] is not False for k in
                      ['independently_validated', 'training_performed', 'runtime_changed']):
        raise ValueError('Unsupported review claims')
    provider = packet['provider']
    if provider['license'] != 'CC-BY-4.0' or len(provider['revision']) != 40:
        raise ValueError('Unpinned source/license')
    checked(root, provider['license_path'], provider['license_sha256'])
    groups = json.loads(checked(root, packet['source_groups'], packet['source_groups_sha256']).read_text())
    if groups['revision'] != provider['revision'] or groups['locked_before_role_detector_inference'] is not True:
        raise ValueError('Source lock changed')
    locked = {s['id']: s for s in groups['sources']}
    if len(locked) != p['expected_new_images'] or {s['id'] for s in packet['sources']} != set(locked) or len(packet['sources']) != len(locked):
        raise ValueError('Source coverage changed')
    clean, quarantined, corrected = clean_rows(base, p['changes'])
    if len(quarantined) != p['expected_quarantined_exposures'] or len(corrected) != p['expected_relabelled_exposures']:
        raise ValueError('Correction exposure count changed')
    # Screen against every old split AND separate v8/v9 heldout release images.
    refs, pixels, files = [], set(), set()
    references = [(base_dir, row) for row in base['files']]
    for release in json.loads(base_protocol.read_text())['source_releases']:
        directory = root/release['directory']
        manifest = json.loads(checked(directory, 'manifest.json', release['manifest_sha256']).read_text())
        references.extend((directory, row) for row in manifest['files'])
    for directory, row in references:
        path = checked(directory, row['image'], row['image_sha256'])
        if digest(path) in files:
            continue
        files.add(digest(path))
        im = cv2.imread(str(path))
        pixels.add(hashlib.sha256(str(im.shape).encode()+im.tobytes()).hexdigest())
        refs.append({'image': path.relative_to(root).as_posix(), **image_feature(im)})
    additions, primary_sizes = [], []
    protected_families = {row['family'] for row in base['files']}
    for source in packet['sources']:
        label = validate_source(source, locked[source['id']])
        if source['scene_family'] in protected_families:
            raise ValueError('Protected family reused')
        ip = checked(root, source['path'], source['sha256'])
        lp = checked(root, source['label_path'], source['label_sha256'])
        if git_blob_sha(ip.read_bytes()) != source['git_blob_sha'] or git_blob_sha(lp.read_bytes()) != source['label_git_blob_sha']:
            raise ValueError('Pinned source blob mismatch')
        image = cv2.imread(str(ip))
        if image is None or image.shape[:2] != (source['height'], source['width']):
            raise ValueError('Source geometry changed')
        x1, y1, x2, y2 = source['roi']
        patch = image[y1:y2, x1:x2]
        pixel = hashlib.sha256(str(patch.shape).encode()+patch.tobytes()).hexdigest()
        native_pixel = hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()
        if pixel in pixels or native_pixel in pixels or duplicate_hits(image_feature(image), refs) or duplicate_hits(image_feature(patch), refs):
            raise ValueError('Duplicate source image')
        pixels.update([pixel, native_pixel])
        refs.extend([{'image': source['id'], **image_feature(im)} for im in [image, patch]])
        additions.append((source, cv2.imencode('.png', patch)[1].tobytes(), label, pixel))
        primary = next(o for o in source['objects'] if o['id'] == source['primary_id'])
        primary_sizes.append({'id': source['id'], 'color': source['primary_color'], 'role': primary['role'],
                              'height_at_640': (primary['xyxy'][3]-primary['xyxy'][1])*640/max(x2-x1, y2-y1)})
    output = (root/p['dataset']).resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Output must be a new workspace directory')
    output.mkdir(parents=True)
    rows = []
    for row, change in clean:
        for k in ['image', 'label']:
            target = output/row[k]
            target.parent.mkdir(parents=True, exist_ok=True)
            original = checked(base_dir, row[k], row[k+'_sha256'])
            if k == 'label' and change:
                text = amend(original.read_bytes().decode('utf-8'), change)
                target.write_bytes(text.encode('utf-8'))
                row['label_sha256'] = digest(target)
                row['class_counts'] = dict(Counter(line.split()[0] for line in text.splitlines()))
                row['annotation_correction_v11'] = change
            else:
                shutil.copyfile(original, target)
        rows.append(row)
    for source, encoded, label, pixel in additions:
        row = {'split': 'train', 'family': source['scene_family'], 'source': source['scene_family'],
               'pixel_sha256': pixel, 'sampling_repeat': 1, 'sampling_origin': 'reviewed_wide_context_v11',
               'class_counts': dict(Counter(line.split()[0] for line in label.splitlines())),
               'provenance': {'review_source': source['id'], 'source_sha256': source['sha256'], 'roi': source['roi'],
                              'annotation_packet_sha256': p['annotation_packet_sha256']}}
        for k, folder, ext, content in [('image', 'images', 'png', encoded), ('label', 'labels', 'txt', label.encode())]:
            row[k] = f'{folder}/train/{source["id"]}.{ext}'
            target = output/row[k]
            target.write_bytes(content)
            row[k+'_sha256'] = digest(target)
        rows.append(row)
    result = {**base, 'kind': 'clean_role_dataset_v11', 'protocol_sha256': digest(protocol_path), 'files': rows,
              'images': dict(Counter(row['split'] for row in rows)), 'v11_quarantined': quarantined,
              'v11_corrected': corrected, 'v11_new_images': len(additions)}
    if protected_rows(result) != protected_rows(base) or any(row.get('match_id') == '128057' for row in rows):
        raise ValueError('Protected data changed')
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    (output/'data.yaml').write_text(yaml_text(output))
    verify_dataset(root, output, protocol_path)
    return write_summary(root, protocol_path, result, packet, primary_sizes, len(files))


def write_summary(root, protocol_path, result, packet, primary_sizes, reference_count):
    """Write diagnostics separately from the immutable materialized dataset."""
    output = root/json.loads(protocol_path.read_text())['dataset']
    rows = result['files']
    summary = {'images': result['images'], 'quarantined': result['v11_quarantined'], 'corrected': result['v11_corrected'],
               'new_images': result['v11_new_images'], 'new_visual_groups': len({s['scene_family'] for s in packet['sources']}),
               'primary_sizes': primary_sizes, 'screened_reference_images': reference_count, 'duplicate_hits': 0,
               'protected_splits_byte_identical': True, 'training_started': False,
               'manifest_sha256': digest(output/'manifest.json'), 'protocol_sha256': digest(protocol_path),
               'train_unit_count': len({(r['pixel_sha256'],r['label_sha256']) for r in rows if r['split']=='train'}),
               'new_box_counts': dict(sum((Counter({int(k):v for k,v in r['class_counts'].items()}) for r in rows if r.get('sampling_origin')=='reviewed_wide_context_v11'), Counter()))}
    (root/'docs/fixtures/role_data_curation_summary_v11.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root, root/'docs/fixtures/role_data_curation_protocol_v11.json'), indent=2))
