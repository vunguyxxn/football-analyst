"""Inventory frozen train units, source-frame overlaps and context for coverage review."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from backend.cv.evaluate_role_detector import checked, digest, iou
from backend.cv.prepare_role_dataset import NAMES, verify_dataset
from backend.cv.role_distribution import size_bin


def unique_train(rows):
    groups={}
    for row in rows:
        if row['split']!='train':continue
        groups.setdefault((row['pixel_sha256'],row['label_sha256']),[]).append(row)
    return list(groups.values())


def parent_box(box,roi):
    a,b,c,d=box
    return [a+roi[0],b+roi[1],c+roi[0],d+roi[1]]


def cluster_boxes(objects):
    """Same parent/role and IoU>=.7, not unique people or verified matches."""
    groups=defaultdict(list)
    for ob in objects:groups[(ob['parent'],ob['role'])].append(ob)
    clusters=[]
    for group in groups.values():
        links=list(range(len(group)))
        def find(i):
            while links[i]!=i:i=links[i]
            return i
        for i,a in enumerate(group):
            for j,b in enumerate(group[:i]):
                if iou(a['parent_xyxy'],b['parent_xyxy'])>=.7:links[find(i)]=find(j)
        components=defaultdict(list)
        for i,ob in enumerate(group):components[find(i)].append(ob)
        for members in components.values():
            representative=max(members,key=lambda ob:(ob['parent_xyxy'][2]-ob['parent_xyxy'][0])*(ob['parent_xyxy'][3]-ob['parent_xyxy'][1]))
            clusters.append({'id':members[0]['id'],'role':representative['role'],'parent':representative['parent'],
                             'parent_xyxy':representative['parent_xyxy'],'members':[ob['id'] for ob in members],
                             'source_height640':representative['source_height640'],
                             'family':representative['family'],'exposures':sum(ob['exposures'] for ob in members)})
    return clusters


def main(root):
    import cv2
    import numpy as np
    pp=root/'docs/fixtures/role_sources_training_protocol_v10.json';p=json.loads(pp.read_text())
    frozen=json.loads((root/'docs/fixtures/role_sources_training_result_v10.json').read_text())
    if digest(pp)!=frozen['protocol_sha256']:raise ValueError('Protocol changed')
    dataset=root/p['dataset'];checked(dataset,'manifest.json',frozen['manifest_sha256']);m=verify_dataset(root,dataset,pp)
    old=json.loads(checked(root,p['annotation_packet'],p['annotation_packet_sha256']).read_text());old_sources={s['id']:s for s in old['sources']}
    full=json.loads(checked(root,p['clean_full_packet'],p['clean_full_packet_sha256']).read_text());full_sources={s['id']:s for s in full['sources']}
    source_split=json.loads(checked(root,p['source_split'],p['source_split_sha256']).read_text());clips={s['match_id']:s for s in source_split['sources']}
    out=root/'data/processed/role_train_coverage_v10';out.mkdir(exist_ok=False)
    objects=[];parents={};units=[];indices=Counter();exposure_counts=defaultdict(Counter);unique_counts=defaultdict(Counter)
    for group in unique_train(m['files']):
        row=group[0];prov=row['provenance'];image=cv2.imread(str(dataset/row['image']));h,w=image.shape[:2]
        context={'type':'image','path':(dataset/row['image']).relative_to(root).as_posix(),'sha256':row['image_sha256']}
        roi=[0,0,w,h];pw,ph=w,h
        if 'annotation_region' in prov:
            s=old_sources[prov['source_id']];roi=prov['roi'];pw,ph=s['width'],s['height']
            context={'type':s['type'],'path':s['source'],'sha256':s['source_sha256']}
            if s['type']=='video_frame':context.update(frame=s['frame'],frame_sha256=s['raw_image_sha256'])
            parent=('video:'+s['source_sha256']+':'+str(s['frame'])) if s['type']=='video_frame' else 'image:'+s['source_sha256']
        elif 'reviewed_full_frame' in prov:
            parent='image:'+full_sources[prov['reviewed_full_frame']]['sha256']
        elif 'released_roi' in prov:
            match_id=row['match_id']
            if clips[match_id]['split']!='train_candidate':raise ValueError('Heldout match in train coverage')
            s=clips[match_id];pw,ph=1280,720;roi=prov['roi'];parent='video:'+s['lfs']['sha256']+':'+str(prov['frame'])
            context={'type':'video_frame','path':'data/raw/role_sources_v8/'+Path(s['rfilename']).name,'sha256':s['lfs']['sha256'],'frame':prov['frame']}
        elif 'video' in prov:parent='video:'+prov['video_sha256']+':'+str(prov['frame'])
        else:parent='image:'+prov['image_sha256']
        if parent not in parents:parents[parent]={'id':len(parents),'family':row['family'],'width':pw,'height':ph,'context':context}
        units.append({'image':row['image'],'label':row['label'],'exposures':len(group),'parent':parent,'roi':roi})
        for label_id,line in enumerate((dataset/row['label']).read_text().splitlines()):
            cls,x,y,bw,bh=map(float,line.split());role=NAMES[int(cls)];height=bh*h*640/max(w,h)
            exposure_counts[role][size_bin(height)]+=len(group);unique_counts[role][size_bin(height)]+=1
            if role=='player':continue
            box=[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h];parent_xyxy=parent_box(box,roi)
            ob={'id':role+'-'+str(indices[role]),'role':role,'index':indices[role],'image':row['image'],'label_id':label_id,
                'image_sha256':row['image_sha256'],'label_sha256':row['label_sha256'],'parent':parent,'family':row['family'],
                'xyxy':box,'parent_xyxy':parent_xyxy,'loaded_height640':height,'source_height640':(parent_xyxy[3]-parent_xyxy[1])*640/max(pw,ph),'exposures':len(group)}
            indices[role]+=1;objects.append(ob)
    clusters=cluster_boxes(objects)
    # Raw contexts are decoded once per parent, never loaded as a whole video.
    tiles=[];verified={}
    for parent,meta in parents.items():
        selected=[c for c in clusters if c['parent']==parent]
        if not selected:continue
        c=meta['context'];path=checked(root,c['path'])
        if c['path'] not in verified:
            if digest(path)!=c['sha256']:raise ValueError('Parent context changed')
            verified[c['path']]=True
        if c['type']=='image':image=cv2.imread(str(path))
        else:
            cap=cv2.VideoCapture(str(path))
            try:cap.set(cv2.CAP_PROP_POS_FRAMES,c['frame']);ok,image=cap.read()
            finally:cap.release()
            if not ok:raise ValueError('Cannot decode parent')
            if c.get('frame_sha256') and hashlib.sha256(cv2.imencode('.png',image)[1].tobytes()).hexdigest()!=c['frame_sha256']:raise ValueError('Parent frame changed')
        if image.shape[:2]!=(meta['height'],meta['width']):raise ValueError('Parent geometry changed')
        meta['context_review_path']=f'parent-{meta["id"]}.jpg'
        marked=image.copy()
        for ob in selected:
            a,b,d,e=map(int,ob['parent_xyxy']);cv2.rectangle(marked,(a,b),(d,e),(0,255,0),2)
            cv2.putText(marked,ob['id'].replace('goalkeeper-','G').replace('referee-','R'),(a,max(20,b-3)),0,.7,(0,255,0),2)
        cv2.imwrite(str(out/meta['context_review_path']),marked)
        view=cv2.resize(marked,(400,225));tile=np.zeros((250,400,3),np.uint8);tile[25:]=view
        cv2.putText(tile,'C'+str(meta['id']),(3,18),0,.5,(255,255,255),1);tiles.append(tile)
    for start in range(0,len(tiles),20):
        chunk=tiles[start:start+20]+[np.zeros((250,400,3),np.uint8)]*(20-len(tiles[start:start+20]))
        cv2.imwrite(str(out/f'contexts-{start//20}.jpg'),np.vstack([np.hstack(chunk[i:i+4]) for i in range(0,20,4)]))
    result={'dataset_manifest_sha256':digest(dataset/'manifest.json'),'protocol_sha256':digest(pp),'units':units,'parents':parents,
            'objects':objects,'clusters':clusters,'image_exposures':sum(u['exposures'] for u in units),'unique_pixel_label_units':len(units),
            'source_parent_frames':len(parents),'box_exposures':dict(exposure_counts),'unique_unit_boxes':dict(unique_counts),
            'scope':'Train only. Cluster same source frame/role atIoU>=.7 to screen overlapping ROI observations, not unique people/matches. Sizes before augmentation at640 long side; loaded crop and source frame geometry separately. Visual family not official match identity.'}
    verify_dataset(root,dataset,pp)
    (out/'inventory.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['image_exposures','unique_pixel_label_units','source_parent_frames','box_exposures','unique_unit_boxes']}));print('clusters',Counter(c['role'] for c in clusters),'context sheets',(len(tiles)+19)//20)


def validate_review(objects,packet):
    expected={o['id']:o for o in objects};reviews=packet['objects']
    if len({r['id'] for r in reviews})!=len(reviews) or {r['id'] for r in reviews}!=set(expected):
        raise ValueError('Visual review must cover each inventory object exactly once')
    for row in reviews:
        ob=expected[row['id']]
        if any(row[k]!=ob[k] for k in ['image_sha256','label_sha256']):raise ValueError('Review bound to different image/label')
        if not row.get('shirt_appearance') or not row.get('context'):raise ValueError('Missing review state; unknown must be explicit')
    return {r['id']:r for r in reviews}


def summarize(root):
    out=root/'data/processed/role_train_coverage_v10';ip=out/'inventory.json';j=json.loads(ip.read_text())
    rp=root/'docs/fixtures/role_train_coverage_review_v10.json';packet=json.loads(rp.read_text())
    if digest(ip)!=packet['inventory_sha256'] or j['dataset_manifest_sha256']!=packet['dataset_manifest_sha256']:
        raise ValueError('Review inventory changed')
    p=json.loads((root/'docs/fixtures/role_sources_training_protocol_v10.json').read_text());dataset=root/p['dataset']
    checked(dataset,'manifest.json',j['dataset_manifest_sha256']);m=verify_dataset(root,dataset,root/'docs/fixtures/role_sources_training_protocol_v10.json')
    by_image={x['image']:x for x in m['files']};reviews=validate_review(j['objects'],packet);appearance={}
    for ob in j['objects']:
        source=by_image[ob['image']]['source']
        actual_prefix=source.split(':')[-1] if source.startswith('external:') else None
        if reviews[ob['id']]['filename_prefix']!=actual_prefix:raise ValueError('Review source prefix differs from manifest')
    for role in ['goalkeeper','referee']:
        rs=[o for o in j['objects'] if o['role']==role];colors={}
        for color in sorted({reviews[o['id']]['shirt_appearance'] for o in rs}):
            subset=[o for o in rs if reviews[o['id']]['shirt_appearance']==color];small=[o for o in subset if o['loaded_height640']<24]
            colors[color]={'unique_unit_boxes':len(subset),'box_exposures':sum(o['exposures'] for o in subset),
                'small_unique_unit_boxes':len(small),'small_box_exposures':sum(o['exposures'] for o in small),
                'source_parent_frames':len({o['parent'] for o in subset}),'families':dict(Counter(o['family'] for o in subset)),
                'small_filename_prefixes':dict(Counter(reviews[o['id']]['filename_prefix'] or 'non_external_or_unknown' for o in small))}
        appearance[role]=colors
    dark=[o for o in j['objects'] if o['role']=='referee' and reviews[o['id']]['shirt_appearance']=='dark']
    far=[o for o in dark if reviews[o['id']]['context']=='far_touchline']
    origins=defaultdict(list)
    for ob in j['objects']:
        row=by_image[ob['image']];origin='reviewed_full_frame' if 'reviewed_full_frame' in row['provenance'] else row['sampling_origin']
        origins[(origin,ob['role'])].append(ob)
    geometry={origin+'/'+role:{'unique_unit_boxes':len(obs),'exposures':sum(o['exposures'] for o in obs),
        'loaded_size_bins':dict(Counter(size_bin(o['loaded_height640']) for o in obs)),
        'source_size_bins':dict(Counter(size_bin(o['source_height640']) for o in obs))} for (origin,role),obs in origins.items()}
    result={'date':'2026-11-04','dataset_manifest_sha256':j['dataset_manifest_sha256'],'inventory_sha256':digest(ip),
        'review_packet_sha256':digest(rp),'image_exposures':j['image_exposures'],'unique_pixel_label_units':j['unique_pixel_label_units'],
        'source_parent_frames':j['source_parent_frames'],'box_exposures':j['box_exposures'],'unique_unit_boxes':j['unique_unit_boxes'],
        'parent_frame_box_clusters':dict(Counter(c['role'] for c in j['clusters'])),'appearance':appearance,'origin_geometry':geometry,
        'dark_referee':{'unique_unit_boxes':len(dark),'exposures':sum(o['exposures'] for o in dark),
            'context_counts':dict(Counter(reviews[o['id']]['context'] for o in dark)),
            'confirmed_far_ids':[o['id'] for o in far],'far_source_frames':len({o['parent'] for o in far}),
            'far_exposures':sum(o['exposures'] for o in far),'far_loaded_small_count':sum(o['loaded_height640']<24 for o in far),
            'far_filename_prefixes':dict(Counter(reviews[o['id']]['filename_prefix'] for o in far)),
            'far_family_counts':dict(Counter(o['family'] for o in far)),
            'remaining_referee_positions_unknown':sum(o['role']=='referee' and reviews[o['id']]['context']=='not_reviewed_for_position' for o in j['objects'])},
        'quality_flags':[rv for rv in packet['objects'] if rv['quality_flag']],'scope':packet['scope'],
        'geometry_scope':j['scope'],'training_performed':False,'labels_modified':False}
    (root/'docs/fixtures/role_train_coverage_summary_v10.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'appearance':appearance,'dark_referee':result['dark_referee'],'origin_geometry':geometry}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',choices=['inventory','summarize'],default='inventory')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    (main if args.action=='inventory' else summarize)(root)
