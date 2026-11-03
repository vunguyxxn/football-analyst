"""Merge frozen v8/v9 train ROIs; preserve every old val/test byte and match split."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from backend.cv.balance_role_dataset import crop_labels, protected_rows
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import verify_dataset, yaml_text
from backend.cv.release_role_sources import match_splits, verify_frame, verify_increment


def select_rows(packet, release, mapping):
    """Bind released labels to reviewed geometry; admit only locked train matches."""
    frames={f['id']:f for f in packet['frames']}
    if len(frames)!=len(packet['frames']):raise ValueError('Duplicate frame ID')
    if {r['id'] for r in release['files']}!=set(frames):raise ValueError('Release/packet coverage differs')
    if release['locked_match_splits']!=mapping:raise ValueError('Release split changed')
    selected=[]
    for row in release['files']:
        frame=frames[row['id']]
        label=verify_frame(frame,mapping)
        if any(row[k]!=frame[k] for k in ['match_id','split','frame']):
            raise ValueError('Released frame identity changed')
        # Release text uses native Windows newlines; both encodings have identical labels.
        label_hashes={hashlib.sha256(text.encode()).hexdigest() for text in [label,label.replace('\n','\r\n')]}
        if row['label_sha256'] not in label_hashes:
            raise ValueError('Released label differs from reviewed ROI')
        if row['split']=='train_candidate':selected.append((row,frame))
    return selected


def prepare(root, protocol_path):
    import cv2
    p=json.loads(protocol_path.read_text())
    base=root/p['merge_dataset']
    checked(base,'manifest.json',p['merge_manifest_sha256'])
    base_manifest=verify_dataset(root,base,checked(root,p['merge_protocol'],p['merge_protocol_sha256']))
    split=checked(root,p['source_split'],p['source_split_sha256'])
    mapping=match_splits(json.loads(split.read_text())['sources'])
    repeats=p['source_roi_repeats']
    if type(repeats) is not int or not 1<=repeats<=4:raise ValueError('ROI repeat cap exceeded')
    additions=[];packets=[];seen=set()
    for spec in p['source_releases']:
        pp=checked(root,spec['packet'],spec['packet_sha256']);packet=json.loads(pp.read_text())
        if packet['source_split_sha256']!=p['source_split_sha256']:raise ValueError('Packet split changed')
        source=root/spec['directory'];mp=checked(source,'manifest.json',spec['manifest_sha256']);release=json.loads(mp.read_text())
        if release['packet_sha256']!=digest(pp):raise ValueError('Release packet changed')
        if packets:verify_increment(packet,packets[0])
        packets.append(packet)
        for row in release['files']:
            key=(row['match_id'],row['frame'])
            if key in seen:raise ValueError('Repeated source frame')
            seen.add(key)
            for k in ['image','label']:checked(source,row[k],row[k+'_sha256'])
        additions.extend((source,row,frame) for row,frame in select_rows(packet,release,mapping))
    if len(additions)!=p['expected_unique_train_rois']:raise ValueError('Train ROI count changed')
    output=root/p['dataset']
    output.mkdir(parents=True,exist_ok=False)
    rows=[]
    def copy(row,source):
        for k in ['image','label']:
            target=output/row[k];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(checked(source,row[k],row[k+'_sha256']),target)
        rows.append(row)
    for row in base_manifest['files']:copy(dict(row),base)
    for source,row,frame in additions:
        image=cv2.imread(str(source/row['image']))
        pixel=hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()
        for rep in range(1,repeats+1):
            merged={'split':'train','family':'soccertrack-match-'+frame['match_id'],
                    'source':'soccertrack-match-'+frame['match_id'],'pixel_sha256':pixel,
                    'match_id':frame['match_id'],'sampling_repeat':rep,'sampling_origin':'reviewed_source_roi',
                    'provenance':{'released_roi':row['id'],'frame':frame['frame'],'roi':frame['roi'],
                                  'source_release':source.relative_to(root).as_posix()},
                    'class_counts':dict(Counter(line.split()[0] for line in crop_labels(frame).splitlines()))}
            # Copy from the released paths, then store a distinct sampled filename.
            for k,folder,ext in [('image','images','png'),('label','labels','txt')]:
                rel=f'{folder}/train/st-{row["id"]}-r{rep}.{ext}'
                target=output/rel;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(checked(source,row[k],row[k+'_sha256']),target)
                merged[k]=rel;merged[k+'_sha256']=digest(target)
            rows.append(merged)
    result={**base_manifest,'kind':'merged_role_sources_v10','protocol_sha256':digest(protocol_path),
            'files':rows,'images':dict(Counter(r['split'] for r in rows)),
            'new_unique_train_rois':len(additions),'new_train_exposures':len(additions)*repeats,
            'locked_match_splits':mapping,'source_roi_repeats':repeats}
    if protected_rows(result)!=protected_rows(base_manifest):raise ValueError('Protected split changed')
    if any(r.get('match_id')=='128057' for r in rows):raise ValueError('Heldout source match leaked')
    (output/'manifest.json').write_text(json.dumps(result,indent=2))
    (output/'data.yaml').write_text(yaml_text(output))
    verify_dataset(root,output,protocol_path)
    summary={k:v for k,v in result.items() if k!='files'}
    summary['manifest_sha256']=digest(output/'manifest.json')
    summary['protocol']='docs/fixtures/role_sources_training_protocol_v10.json'
    summary['training_started']=False
    (root/'docs/fixtures/role_sources_training_plan_v10.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    prepare(root,root/'docs/fixtures/role_sources_training_protocol_v10.json')
