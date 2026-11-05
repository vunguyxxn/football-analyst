"""Prepare a separate parent-aware v11+v12+v13 dataset; no training/inference."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil

from backend.cv.balance_role_dataset import protected_rows
from backend.cv.curate_role_counterexamples import duplicate_hits, image_feature
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import NAMES, audit, verify_dataset, yaml_text
from backend.cv.prepare_role_source_release_v12 import pixel_hash, reviewed_regions


def allocate(rows, budget=2):
    """One exposure per reviewed ROI; shared parents count toward the same cap."""
    groups = defaultdict(list)
    for row in rows:
        if row['split'] != 'train':
            raise ValueError('New releases must be train only')
        groups[row['parent']].append(row)
    result = []
    for parent, group in sorted(groups.items()):
        if len(group) > budget or (len(group) > 1 and sorted(r['negative'] for r in group) != [False, True]):
            raise ValueError('Parent exceeds reviewed positive/negative ROI cap')
        result.extend((row, 1) for row in group)
    return result


def base_parents(root, protocol, rows):
    v11 = json.loads(checked(root, protocol['reference_training_protocol'], protocol['reference_training_protocol_sha256']).read_text())
    v10 = json.loads(checked(root, v11['reference_training_protocol'], v11['reference_training_protocol_sha256']).read_text())
    def packet(key):
        return json.loads(checked(root, v10[key], v10[key+'_sha256']).read_text())
    old = {s['id']: s for s in packet('annotation_packet')['sources']}
    full = {s['id']: s for s in packet('clean_full_packet')['sources']}
    clips = {s['match_id']: s for s in packet('source_split')['sources']}
    result = {}
    for row in rows:
        v = row['provenance']
        if 'annotation_region' in v:
            source = old[v['source_id']]
            parent = ('video:'+source['source_sha256']+':'+str(source['frame'])) if source['type']=='video_frame' else 'image:'+source['source_sha256']
        elif 'reviewed_full_frame' in v:
            parent = 'image:'+full[v['reviewed_full_frame']]['sha256']
        elif 'released_roi' in v:
            parent = 'video:'+clips[row['match_id']]['lfs']['sha256']+':'+str(v['frame'])
        elif 'video' in v:
            parent = 'video:'+v['video_sha256']+':'+str(v['frame'])
        else:
            parent = 'image:'+v.get('source_sha256', v.get('image_sha256'))
        result[row['image']] = parent
    return result


def exposure(row):
    return {k: row[k] for k in ['image','image_sha256','label_sha256','sampling_parent','family']}


def validate_sampling(root, protocol, manifest):
    ledger = json.loads(checked(root, protocol['parent_sampling'], protocol['parent_sampling_sha256']).read_text())
    actual = [exposure(r) for r in manifest['files'] if r['split']=='train']
    if actual != ledger['exposures'] or dict(Counter(r['sampling_parent'] for r in actual)) != ledger['parent_exposures']:
        raise ValueError('Locked parent sampling changed')
    if manifest['images'] != protocol['expected_images']:
        raise ValueError('Locked split counts changed')
    splits = {}
    for row in manifest['files']:
        if str(row.get('match_id')) == '128057':
            raise ValueError('Heldout match excluded from merged dataset')
        parent = row['sampling_parent']
        if not isinstance(parent,str) or parent.endswith(':None'):
            raise ValueError('Missing source parent identity')
        if parent in splits and splits[parent] != row['split']:
            raise ValueError('Parent crosses split')
        splits[parent] = row['split']
    if dict(Counter(r['split'] for r in manifest['files'])) != protocol['expected_images']:
        raise ValueError('Materialized split counts changed')
    audit(manifest['files'])


def label_counts(path):
    import math
    counts = Counter()
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 5 or parts[0] not in {'0','1','2'}:
            raise ValueError('Invalid three-role label')
        x,y,w,h = map(float, parts[1:])
        if not all(math.isfinite(v) for v in [x,y,w,h]) or not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            raise ValueError('Invalid normalized geometry')
        if min(x-w/2,y-h/2) < -1e-8 or max(x+w/2,y+h/2) > 1+1e-8:
            raise ValueError('Label outside image')
        counts[NAMES[int(parts[0])]] += 1
    return counts


def prepare(root, protocol_path, output=None):
    import cv2
    p = json.loads(protocol_path.read_text())
    for spec in p['models'] + list(p['comparison_references'].values()):
        checked(root,spec['path'],spec['sha256'])
    destination = (output or root/p['dataset']).resolve()
    if not destination.is_relative_to(root) or destination.exists() or (destination.parent/'summary.json').exists():
        raise ValueError('New workspace output required')
    base_dir = checked(root, p['curated_dataset']+'/manifest.json', p['curated_manifest_sha256']).parent
    base_pp = checked(root, p['curation_protocol'], p['curation_protocol_sha256'])
    base = verify_dataset(root, base_dir, base_pp)
    parents = base_parents(root, p, base['files'])
    rows = [{**r, 'sampling_parent': parents[r['image']]} for r in base['files']]
    # Check all old splits and source-heldout files, with no detector inference.
    references = [(base_dir, r) for r in base['files']]
    for spec in p['source_releases']:
        directory = checked(root, spec['directory']+'/manifest.json', spec['manifest_sha256']).parent
        checked(root, spec['packet'], spec['packet_sha256'])
        references.extend((directory,r) for r in json.loads((directory/'manifest.json').read_text())['files'])
    seen, pixels, features = set(), set(), []
    for directory, row in references:
        for key in ['image','label']:
            checked(directory,row[key],row[key+'_sha256'])
        if row['image_sha256'] in seen:
            continue
        seen.add(row['image_sha256'])
        image = cv2.imread(str(directory/row['image']))
        if image is None:
            raise ValueError('Unreadable reference image')
        pixels.add(pixel_hash(image)); features.append({'image':row['image'], **image_feature(image)})
    screened = len(seen)
    protected_pixels = set(pixels)
    additions = []
    source_units = []
    for release in p['merge_releases']:
        directory = checked(root, release['directory']+'/manifest.json', release['manifest_sha256']).parent
        packet = json.loads(checked(root, release['packet'], release['packet_sha256']).read_text())
        sources = {s['id']:s for s in packet['sources']}
        provider = packet['provider']
        checked(root, provider['license_path'], provider['license_sha256'])
        group = json.loads(checked(root, packet['source_groups'], packet['source_groups_sha256']).read_text())
        if not group['locked_before_role_detector_inference']:
            raise ValueError('Source groups not locked')
        released = json.loads((directory/'manifest.json').read_text())
        expected = {}
        for source in sources.values():
            native = cv2.imread(str(checked(root, source['path'], source['sha256'])))
            if native is None or native.shape[:2] != (source['height'],source['width']):
                raise ValueError('Source image geometry changed')
            if source['sha256'] in seen or pixel_hash(native) in pixels or duplicate_hits(image_feature(native),features):
                raise ValueError('Duplicate source parent')
            # Screen each parent against every previous parent; shared ROI29 stays one parent.
            seen.add(source['sha256']); pixels.add(pixel_hash(native))
            features.append({'image':source['id'],'parent':source['id'], **image_feature(native)})
            label = checked(root, source['label_path'], source['label_sha256']).read_text()
            for region in reviewed_regions(source,label):
                a,b,c,d = region['roi']; patch = native[b:d,a:c]
                other_features = [f for f in features if f.get('parent',f['image']) != source['id']]
                if pixel_hash(patch) in protected_pixels or duplicate_hits(image_feature(patch),other_features):
                    raise ValueError('Duplicate ROI from another parent')
                features.append({'image':region['id'],'parent':source['id'],**image_feature(patch)})
                expected[region['id']] = (source,region,pixel_hash(patch))
        if {Path(r['image']).stem for r in released['files']} != set(expected):
            raise ValueError('Release ROI coverage changed')
        for row, repeat in allocate(released['files'], p['new_parent_roi_cap']):
            source, region, pixel = expected[Path(row['image']).stem]
            for key in ['image','label']:
                checked(directory,row[key],row[key+'_sha256'])
            image = cv2.imread(str(directory/row['image']))
            if (directory/row['label']).read_text() != region['labels'] or pixel != row['pixel_sha256'] or pixel_hash(image) != pixel:
                raise ValueError('Release pixels/labels differ from reviewed ROI')
            if row['roi'] != region['roi'] or row['parent'] != source['id'] or row['family'] != source['scene_family'] or row['negative'] != region['negative']:
                raise ValueError('Release parent/scene/ROI changed')
            counts = label_counts(directory/row['label'])
            if bool(counts) == row['negative'] or dict(counts) != row['class_counts']:
                raise ValueError('Negative or class counts changed')
            new = {**row, 'source':row['family'], 'sampling_origin':'reviewed_release_v14',
                   'sampling_repeat':repeat, 'sampling_parent':'image:'+source['sha256'],
                   'class_counts':{str(NAMES.index(k)):v for k,v in counts.items()},
                   'provenance':{'source_sha256':source['sha256'],'roi':row['roi'],
                                 'release_manifest_sha256':release['manifest_sha256']}}
            additions.append((directory,row,new)); rows.append(new)
            source_units.append({'parent':new['sampling_parent'],'family':row['family'],'image':row['image'],
                                 'negative':row['negative'],'class_counts':dict(counts)})
    result = {**base,'kind':'parent_locked_role_dataset_v14','protocol_sha256':digest(protocol_path),
              'images':dict(Counter(r['split'] for r in rows)),'files':rows}
    if protected_rows(result) != protected_rows(base):
        raise ValueError('Protected data changed')
    validate_sampling(root,p,result)
    # Validate labels and recompute distribution from bytes, including legacy records without counts.
    distributions = defaultdict(Counter); units = defaultdict(dict); negative = Counter()
    for directory, old, row in [(base_dir,r,n) for r,n in zip(base['files'],rows)] + additions:
        counts = label_counts(directory/old['label']); split = row['split']
        distributions[split].update(counts)
        units[split][(row['pixel_sha256'],row['label_sha256'])] = counts
        if not counts:negative[split] += 1
    destination.mkdir(parents=True)
    for directory, old, new in [(base_dir,r,r) for r in base['files']] + additions:
        for key in ['image','label']:
            target=destination/new[key];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(checked(directory,old[key],old[key+'_sha256']),target)
    (destination/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (destination/'data.yaml').write_text(yaml_text(destination))
    verify_dataset(root,destination,protocol_path)
    verify_dataset(root,base_dir,base_pp)
    for spec in p['merge_releases']:
        directory=root/spec['directory']
        m=json.loads(checked(directory,'manifest.json',spec['manifest_sha256']).read_text())
        for row in m['files']:
            for key in ['image','label']:checked(directory,row[key],row[key+'_sha256'])
    summary = {'kind':'role_dataset_merge_summary_v14','protocol_sha256':digest(protocol_path),
               'manifest_sha256':digest(destination/'manifest.json'),'parent_sampling_sha256':p['parent_sampling_sha256'],
               'images':result['images'],'unique_pixel_label_units':{s:len(u) for s,u in units.items()},
               'parent_frames':{s:len({r['sampling_parent'] for r in rows if r['split']==s}) for s in distributions},
               'scene_families':{s:len({r['family'] for r in rows if r['split']==s}) for s in distributions},
               'class_box_exposures':{s:dict(c) for s,c in distributions.items()},
               'unique_unit_class_boxes':{s:dict(sum(u.values(),Counter())) for s,u in units.items()},
               'negative_exposures':dict(negative),
               'negative_unique_units':{s:sum(not c for c in u.values()) for s,u in units.items()},
               'new_source_units':source_units,'new_parent_frames':len({r['parent'] for r in source_units}),
               'new_scene_groups':len({r['family'] for r in source_units}),
               'prior_unique_images_screened':screened,'duplicate_parent_hits':0,
               'protected_splits_byte_identical':True,'legacy_train_records_preserved':True,
               'training_started':False,'runtime_changed':False,'independently_validated':False}
    (destination.parent/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (destination.parent/'ATTRIBUTION.md').write_text('Frozen v11 provenance retained. Additions v12/v13: skaczylo/Football-Image-Dataset, CC-BY-4.0, revision 264212872f1bfa6a9a3413f298793474da741aec. See pinned review packets and original release attribution.\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root,root/'docs/fixtures/role_sources_training_protocol_v14.json',args.output),indent=2))
