"""Export reviewed full-frame role labels, preserving native image resolution."""
import json
import shutil
import zipfile
from pathlib import Path
from collections import Counter

from backend.cv.curate_role_counterexamples import duplicate_hits, git_blob_sha, image_feature
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import NAMES
from backend.cv.validate_referee_annotations import box_inside


def labels(source):
    if source['review_status'] != 'agent_reviewed' or source.get('uncertain_boxes'):
        raise ValueError('Full-frame coverage requires resolved review')
    width, height = source['width'], source['height']
    ids, boxes, lines = set(), set(), []
    for obj in source['objects']:
        box_inside(obj['xyxy'], [0,0,width,height])
        if obj['id'] in ids or tuple(obj['xyxy']) in boxes:
            raise ValueError('Duplicate object')
        ids.add(obj['id']); boxes.add(tuple(obj['xyxy']))
        a,b,c,d = obj['xyxy']
        lines.append(f'{NAMES.index(obj["role"])} {(a+c)/2/width:.9f} {(b+d)/2/height:.9f} {(c-a)/width:.9f} {(d-b)/height:.9f}')
    if not lines:
        raise ValueError('No reviewed targets')
    return '\n'.join(lines)+'\n'


def export(root, packet_relative='docs/fixtures/full_frame_roles_v4.json', output_relative='data/processed/full_frame_roles_v4'):
    import cv2
    packet_path = checked(root, packet_relative)
    packet = json.loads(packet_path.read_text())
    base = root / packet['protected_dataset']
    manifest = json.loads(checked(base,'manifest.json',packet['protected_manifest_sha256']).read_text())
    references=[]
    for row in manifest['files']:
        for key in ('image','label'):
            checked(base,row[key],row[key+'_sha256'])
        if row['split'] != 'train':
            references.append({'image':row['image'],**image_feature(cv2.imread(str(base/row['image'])))})
    providers={p['id']:p for p in packet['providers']}
    for p in providers.values():
        if p['license'] != 'CC-BY-4.0':
            raise ValueError('Unregistered license')
        checked(root,p['license_file'],p['license_sha256'])
        if p.get('archive'):
            checked(root,p['archive'],p['archive_sha256'])
    output=(root/output_relative).resolve()
    if not output.is_relative_to(root):
        raise ValueError('Output must stay in workspace')
    if output.exists():
        raise FileExistsError(output)
    rows=[]; counts=Counter(); sizes=Counter()
    for source in packet['sources']:
        if source['split'] != 'train' or source['scene_family'] in {r['family'] for r in manifest['files'] if r['split']!='train'}:
            raise ValueError('Protected split source')
        text=labels(source)
        path=checked(root,source['local_path'],source['sha256'])
        provider=providers[source['provider']]
        if source.get('git_blob_sha'):
            if git_blob_sha(path.read_bytes()) != source['git_blob_sha']:
                raise ValueError('Source provenance changed')
        else:
            with zipfile.ZipFile(root/provider['archive']) as archive:
                if archive.read(source['archive_entry']) != path.read_bytes():
                    raise ValueError('Archive member changed')
        image=cv2.imread(str(path))
        if image.shape[:2] != (source['height'],source['width']) or duplicate_hits(image_feature(image),references):
            raise ValueError('Dimensions changed or protected near-image overlap')
        for key in ('images','labels'):
            (output/key/'train').mkdir(parents=True,exist_ok=True)
        target=output/'images/train'/f'{source["id"]}.jpg'
        label=output/'labels/train'/f'{source["id"]}.txt'
        shutil.copyfile(path,target);label.write_text(text)
        for obj in source['objects']:
            counts[obj['role']]+=1
            h=(obj['xyxy'][3]-obj['xyxy'][1])*640/max(source['width'],source['height'])
            sizes['under24' if h<24 else '24to48' if h<48 else '48plus']+=1
        rows.append({'id':source['id'],'image_sha256':digest(target),'label_sha256':digest(label),'objects':len(source['objects'])})
    result={'images':len(rows),'objects':dict(counts),'height_at_640':dict(sizes),'files':rows,'packet_sha256':digest(packet_path),
            'protected_images_screened':len(references),'training_performed':False,'independently_validated':False,'native_pixels_preserved':True}
    (output/'manifest.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',default='docs/fixtures/full_frame_roles_v4.json')
    parser.add_argument('--output',default='data/processed/full_frame_roles_v4')
    args=parser.parse_args()
    export(Path(__file__).resolve().parents[2],args.packet,args.output)
