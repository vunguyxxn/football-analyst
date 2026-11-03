"""Release source-pinned reviewed ROIs while excluding entire heldout match IDs."""
from collections import Counter
import json
from pathlib import Path

from backend.cv.balance_role_dataset import crop_labels
from backend.cv.curate_role_counterexamples import duplicate_hits, image_feature
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.validate_referee_annotations import box_inside


def match_splits(sources):
    mapping={}
    for s in sources:
        if s['split'] not in ['train_candidate','heldout_review']:
            raise ValueError('Unsupported source split')
        if s['match_id'] in mapping and mapping[s['match_id']]!=s['split']:
            raise ValueError('Same match in train and heldout, including another half/clip')
        mapping[s['match_id']]=s['split']
    return mapping


def verify_frame(frame,mapping):
    if mapping.get(frame['match_id'])!=frame['split']:
        raise ValueError('Frame split differs from locked match assignment')
    if frame['review_status']!='agent_reviewed':raise ValueError('Unreviewed frame')
    box_inside(frame['roi'],[0,0,1280,720])
    if len({o['id'] for o in frame['objects']})!=len(frame['objects']):raise ValueError('Duplicate target ID')
    return crop_labels(frame)


def verify_increment(packet, previous):
    """A later review may add frames, but cannot recycle old observations."""
    old={(f['match_id'],f['frame']) for f in previous['frames']}
    new=[(f['match_id'],f['frame']) for f in packet['frames']]
    if len(set(new))!=len(new) or old.intersection(new):
        raise ValueError('Repeated reviewed source frame')
    if packet['source_split_sha256']!=previous['source_split_sha256']:
        raise ValueError('Increment changed locked source split')


def main(root, packet_relative='docs/fixtures/role_sources_review_v8.json',
         output_relative='data/processed/role_source_release_v8'):
    import cv2
    packet_path=checked(root,packet_relative)
    packet=json.loads(packet_path.read_text())
    if 'previous_packet' in packet:
        previous=checked(root,packet['previous_packet'],packet['previous_packet_sha256'])
        verify_increment(packet,json.loads(previous.read_text()))
    split_path=checked(root,packet['source_split'],packet['source_split_sha256'])
    sources=json.loads(split_path.read_text());mapping=match_splits(sources['sources'])
    for prefix in ['provider_license_readme','upstream_license']:
        key=prefix+'_file' if prefix=='upstream_license' else prefix
        checked(root,packet[key],packet[prefix+'_sha256'])
    if len(sources['revision'])!=40:raise ValueError('Unpinned source')
    base=root/'data/processed/role_clean_dataset_v6'
    old=json.loads((base/'manifest.json').read_text());references=[];seen=set()
    for row in old['files']:
        for key in ['image','label']:checked(base,row[key],row[key+'_sha256'])
        if row['image_sha256'] not in seen:
            references.append({'image':row['image'],**image_feature(cv2.imread(str(base/row['image'])))})
            seen.add(row['image_sha256'])
    paths={}
    for s in sources['sources']:
        name=Path(s['rfilename']).name
        if not name.startswith('st'+s['match_id']+'_'):raise ValueError('Clip/match naming mismatch')
        path=checked(root,'data/raw/role_sources_v8/'+name,s['lfs']['sha256'])
        paths[s['match_id']]=path
    output=(root/output_relative).resolve()
    if not output.is_relative_to(root.resolve()):raise ValueError('Foreign output path')
    output.mkdir(exist_ok=False)
    rows=[];counts=Counter();colours={'player':(255,200,0),'goalkeeper':(0,255,0),'referee':(0,0,255)}
    for f in packet['frames']:
        label=verify_frame(f,mapping);cap=cv2.VideoCapture(str(paths[f['match_id']]))
        try:
            if cap.get(cv2.CAP_PROP_FRAME_COUNT)!=750 or cap.get(cv2.CAP_PROP_FPS)!=25:raise ValueError('Clip time base changed')
            cap.set(cv2.CAP_PROP_POS_FRAMES,f['frame']);ok,image=cap.read()
            if not ok:raise ValueError('Cannot decode reviewed frame')
        finally:cap.release()
        # Reproduce frozen PNG encoding of decoded native frame before cropping.
        import hashlib
        if hashlib.sha256(cv2.imencode('.png',image)[1].tobytes()).hexdigest()!=f['source_frame_sha256']:
            raise ValueError('Decoded source frame changed')
        if duplicate_hits(image_feature(image),references):raise ValueError('New frame overlaps existing corpus by near-image screen')
        a,b,c,d=f['roi'];patch=image[b:d,a:c]
        group='train' if f['split']=='train_candidate' else 'heldout'
        ip=output/f'images/{group}/{f["id"]}.png';lp=output/f'labels/{group}/{f["id"]}.txt'
        ip.parent.mkdir(parents=True,exist_ok=True);lp.parent.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(ip),patch);lp.write_text(label)
        overlay=patch.copy()
        for ob in f['objects']:
            x,y,z,t=map(int,ob['xyxy']);cv2.rectangle(overlay,(x-a,y-b),(z-a,t-b),colours[ob['role']],1)
            counts[f['split']+'/'+ob['role']]+=1
        cv2.imwrite(str(output/f'{f["id"]}-review.jpg'),overlay)
        rows.append({'id':f['id'],'match_id':f['match_id'],'split':f['split'],'frame':f['frame'],'image':ip.relative_to(output).as_posix(),
                     'label':lp.relative_to(output).as_posix(),'image_sha256':digest(ip),'label_sha256':digest(lp),'targets':len(f['objects'])})
    result={'kind':packet.get('release_kind','role_source_release_v8'),'packet_sha256':digest(packet_path),'locked_match_splits':mapping,'files':rows,'counts':dict(counts),
            'prior_unique_images_screened':len(references),'training_performed':False,'heldout_role_detector_evaluated':False,
            'independently_validated':False,'scope':'New real-footage virtual-followcam domain; sparse COCO-assisted agent role labels. Train candidate and heldout match groups never merged. Not raw broadcast accuracy.'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',default='docs/fixtures/role_sources_review_v8.json')
    parser.add_argument('--output',default='data/processed/role_source_release_v8')
    args=parser.parse_args()
    main(Path(__file__).resolve().parents[2],args.packet,args.output)
