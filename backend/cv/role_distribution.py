"""Audit actual training geometry separately from repeated exposures and colour metadata."""
from collections import Counter, defaultdict
import json
from pathlib import Path

from backend.cv.prepare_role_dataset import NAMES, verify_dataset
from backend.cv.evaluate_role_detector import digest


def size_bin(height):
    return 'under24' if height<24 else '24to48' if height<48 else '48plus'


def main(root):
    import cv2
    dataset=root/'data/processed/role_clean_dataset_v6'
    manifest=verify_dataset(root,dataset,root/'docs/fixtures/role_clean_training_protocol_v6.json')
    packet=json.loads((root/'docs/fixtures/referee_annotations_v2.json').read_text())
    regions={r['id']:r for r in packet['regions']}
    result={};colours=Counter();unique_colours={};source_counts=Counter()
    for split in ['train','val','test']:
        exposure=defaultdict(Counter);unique=defaultdict(Counter);seen=set();origin_counts=Counter()
        for row in manifest['files']:
            if row['split']!=split:continue
            image=cv2.imread(str(dataset/row['image']));h,w=image.shape[:2]
            signature=(row['pixel_sha256'],row['label_sha256'])
            fresh=signature not in seen;seen.add(signature)
            origin='reviewed_full_frame' if 'reviewed_full_frame' in row['provenance'] else row.get('sampling_origin','unknown')
            origin_counts[origin]+=1
            if split=='train':source_counts[row['family']]+=1
            for line in (dataset/row['label']).read_text().splitlines():
                role,x,y,bw,bh=map(float,line.split());name=NAMES[int(role)];b=size_bin(bh*h*640/max(w,h))
                exposure[name][b]+=1
                if fresh:unique[name][b]+=1
            region=regions.get(row['provenance'].get('annotation_region'))
            if split=='train' and region and region['kind']=='referee':
                colour=region['attributes']['shirt_color'];colours[colour]+=1;unique_colours[region['id']]=colour
        result[split]={'image_exposures':sum(origin_counts.values()),'unique_pixel_label_units':len(seen),
                       'origin_exposures':dict(origin_counts),'box_exposures':{k:dict(v) for k,v in exposure.items()},
                       'unique_unit_boxes':{k:dict(v) for k,v in unique.items()}}
    report={'dataset_manifest_sha256':digest(dataset/'manifest.json'),'splits':result,'train_family_exposures':dict(source_counts),
            'reviewed_referee_roi_colour_exposures':dict(colours),'reviewed_referee_roi_unique_colours':dict(Counter(unique_colours.values())),
            'colour_scope':'Only main referee subjects with existing reviewed ROI colour metadata. No complete colour annotation for base full-frame boxes; unrecorded is unknown, not absence.',
            'geometry_scope':'BBox height at longest-side640 before augmentation. Unique pixel+label units are not unique people/matches. Overlapping crops remain separate units.'}
    (root/'docs/fixtures/role_distribution_v6.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main(Path(__file__).resolve().parents[2])
