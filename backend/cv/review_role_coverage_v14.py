"""Offline v14 parent inventory and locked visual-review sample; no detector calls."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path

from backend.cv.audit_role_train_coverage import cluster_boxes,unique_train
from backend.cv.evaluate_role_detector import checked,digest,iou
from backend.cv.finetune_roles import write_json
from backend.cv.prepare_role_dataset import NAMES
from backend.cv.role_distribution import size_bin
from backend.cv.run_role_training_v14 import load_plan

OUT='data/processed/role_coverage_review_v14'
LOCK='docs/fixtures/role_coverage_review_plan_v14.json'
REVIEW='docs/fixtures/role_coverage_review_v14.json'


def rank(value):return hashlib.sha256(('coverage-v14-20261105:'+value).encode()).hexdigest()


def choose_parents(parents,new_parents):
    chosen=set(new_parents)
    for family,number in [('red_stadiums',4),('euro_red_white',2),('soccertrack-match-117093',1),('soccertrack-match-118575',1)]:
        eligible=sorted((p for p,m in parents.items() if m['family']==family and p not in chosen),key=rank)
        if len(eligible)<number:raise ValueError('Insufficient parent stratum')
        chosen.update(eligible[:number])
    return sorted(chosen)


def heights(box,roi,parent_width,parent_height):
    h=box[3]-box[1];loaded=max(roi[2]-roi[0],roi[3]-roi[1]);source=max(parent_width,parent_height)
    if h<=0 or min(loaded,source)<=0:raise ValueError('Invalid geometry')
    return {f'{scope}_height{size}':h*size/denominator for scope,denominator in [('loaded',loaded),('source',source)] for size in [640,1280]}


def inventory(root):
    import cv2
    plan,p,m,dataset=load_plan(root)
    out=root/OUT
    if out.exists() or (root/LOCK).exists():raise ValueError('New inventory and lock required')
    old_summary=json.loads((root/'docs/fixtures/role_train_coverage_summary_v10.json').read_text())
    old=json.loads(checked(root,'data/processed/role_train_coverage_v10/inventory.json',old_summary['inventory_sha256']).read_text())
    old_review=json.loads(checked(root,'docs/fixtures/role_train_coverage_review_v10.json',old_summary['review_packet_sha256']).read_text())
    reviews={r['id']:r for r in old_review['objects']}
    inherited={(o['image_sha256'],o['role'],o['label_id']):(o,reviews[o['id']]) for o in old['objects']}
    metadata={k:dict(v) for k,v in old['parents'].items()}
    for version in ['v11','v12','v13']:
        pp=root/f'docs/fixtures/role_sources_review_{version}.json';packet=json.loads(pp.read_text())
        for source in packet['sources']:
            metadata['image:'+source['sha256']]={'family':source['scene_family'],'width':source['width'],'height':source['height'],
              'context':{'type':'image','path':source['path'],'sha256':source['sha256']}}
    parents={};units=[];objects=[];counts=Counter();new_parents=set();duplicates=[]
    for group in unique_train(m['files']):
        row=group[0];parent=row['sampling_parent'];meta=metadata[parent]
        if parent.startswith('video:') and parent.endswith(':128057'):raise ValueError('Unexpected heldout parent')
        if str(row.get('match_id'))=='128057':raise ValueError('Heldout excluded')
        im=cv2.imread(str(dataset/row['image']));h,w=im.shape[:2]
        roi=row['provenance'].get('roi',[0,0,w,h])
        if [roi[2]-roi[0],roi[3]-roi[1]]!=[w,h]:raise ValueError('ROI dimensions changed')
        if row.get('sampling_origin') in {'reviewed_wide_context_v11','reviewed_release_v14'}:new_parents.add(parent)
        parents.setdefault(parent,{'family':row['family'],'width':meta['width'],'height':meta['height'],'context':meta['context'],'units':[]})
        unit={'id':len(units),'parent':parent,'family':row['family'],'image':row['image'],'label':row['label'],
              'image_sha256':row['image_sha256'],'label_sha256':row['label_sha256'],'roi':roi,'exposures':len(group),
              'objects':[],'origin':row.get('sampling_origin','legacy_full_scene')}
        units.append(unit);parents[parent]['units'].append(unit['id'])
        for label_id,line in enumerate((dataset/row['label']).read_text().splitlines()):
            c,x,y,bw,bh=map(float,line.split());role=NAMES[int(c)]
            box=[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]
            parentbox=[box[0]+roi[0],box[1]+roi[1],box[2]+roi[0],box[3]+roi[1]]
            ob={'id':role+'-'+str(counts[role]),'role':role,'unit_id':unit['id'],'label_id':label_id,
                'image':row['image'],'image_sha256':row['image_sha256'],'label_sha256':row['label_sha256'],
                'parent':parent,'family':row['family'],'xyxy':box,'parent_xyxy':parentbox,'roi':roi,'exposures':len(group),
                **heights(parentbox,roi,meta['width'],meta['height'])}
            prior=inherited.get((row['image_sha256'],role,label_id))
            if prior and max(abs(a-b) for a,b in zip(prior[0]['xyxy'],box))<1e-5:
                ob['prior_visual']={k:prior[1][k] for k in ['shirt_appearance','context','quality_flag']}
                ob['prior_visual']['old_id']=prior[0]['id'];ob['prior_visual']['label_hash_rebound']=prior[0]['label_sha256']!=row['label_sha256']
            else:ob['prior_visual']=None
            counts[role]+=1;unit['objects'].append(ob['id']);objects.append(ob)
        obs=objects[-len(unit['objects']):] if unit['objects'] else []
        for i,a in enumerate(obs):
            for b in obs[i+1:]:
                overlap=iou(a['xyxy'],b['xyxy'])
                if overlap>.9:duplicates.append({'a':a['id'],'b':b['id'],'unit_id':unit['id'],'iou':overlap})
    clusters=cluster_boxes(objects)
    sampled=choose_parents(parents,new_parents)
    players=[]
    for parent in sampled:
        group=sorted((c for c in clusters if c['parent']==parent and c['role']=='player'),key=lambda c:rank(c['id']+parent))
        players.extend(c['id'] for c in group[:4])
    selected=[o['id'] for o in objects if o['role']=='goalkeeper' or (o['role']=='referee' and (not o['prior_visual'] or o['prior_visual']['shirt_appearance']=='dark'))]+players
    out.mkdir(parents=True)
    j={'kind':'role_coverage_inventory_v14','manifest_sha256':plan['manifest_sha256'],'protocol_sha256':plan['protocol_sha256'],
       'dataset':plan['training_dataset'],'parents':parents,'units':units,'objects':objects,'clusters':clusters,
       'duplicate_candidates_iou_gt90':duplicates,'old_inventory_sha256':old_summary['inventory_sha256'],
       'old_review_sha256':old_summary['review_packet_sha256'],'training_performed':False,'labels_modified':False}
    write_json(out/'inventory.json',j)
    lock={'kind':'role_coverage_review_plan_v14','locked_before_visual_review':True,'inventory_sha256':digest(out/'inventory.json'),
          'manifest_sha256':plan['manifest_sha256'],'parent_sample':sampled,'new_parents_included':sorted(new_parents),
          'object_sample':selected,'player_sample':players,'seed':'coverage-v14-20261105',
          'method':'All keeper unit boxes; all inherited dark referee boxes plus every unbound/new referee. All13 v11-v13 parents plus hash-ranked4red_stadiums,2euro_red_white,1each train soccertrack group for coverage; max4player spatial clusters per sampled parent by hash. No model scores/val images used.',
          'scope':'Full train label/geometry inventory. Visual coverage audit only selected parent ROI unions; not whole-dataset label acceptance. Prior color metadata reused where pixel/role/index/geometry match; other referee positions remain unknown.',
          'independent_acceptance':'pending_external_human','training_performed':False,'sampling_changed':False}
    write_json(root/LOCK,lock)
    export_evidence(root,j,lock)
    print(json.dumps({'units':len(units),'parents':len(parents),'objects':dict(counts),'clusters':dict(Counter(c['role'] for c in clusters)),
                      'sampled_parents':len(sampled),'player_sample':len(players),'review_objects':len(selected),'duplicate_candidates':len(duplicates)}))


def source_frame(root,meta):
    import cv2
    context=meta['context'];path=checked(root,context['path'],context['sha256'])
    if context['type']=='image':image=cv2.imread(str(path))
    else:
        cap=cv2.VideoCapture(str(path))
        try:cap.set(cv2.CAP_PROP_POS_FRAMES,context['frame']);ok,image=cap.read()
        finally:cap.release()
        if not ok:raise ValueError('Frame decode failed')
        if context.get('frame_sha256'):
            encoded=cv2.imencode('.png',image)[1].tobytes()
            if hashlib.sha256(encoded).hexdigest()!=context['frame_sha256']:raise ValueError('Raw frame pixels changed')
    if image.shape[:2]!=(meta['height'],meta['width']):raise ValueError('Parent shape changed')
    return image


def export_evidence(root,j,lock):
    import cv2
    import numpy as np
    out=root/OUT;dataset=root/j['dataset'];byid={o['id']:o for o in j['objects']}
    for role in NAMES:
        selected=[byid[k] for k in lock['object_sample'] if byid[k]['role']==role];tiles=[]
        for o in selected:
            im=cv2.imread(str(dataset/o['image']));h,w=im.shape[:2];a,b,c,d=map(int,o['xyxy']);x,y=max(0,a-65),max(0,b-55)
            crop=im[y:min(h,d+55),x:min(w,c+65)].copy();cv2.rectangle(crop,(a-x,b-y),(c-x,d-y),(0,255,255),1)
            cv2.imwrite(str(out/(o['id']+'.jpg')),crop)
            scale=min(270/crop.shape[1],185/crop.shape[0]);crop=cv2.resize(crop,None,fx=scale,fy=scale)
            tile=np.full((225,280,3),25,np.uint8);tile[22:22+crop.shape[0],:crop.shape[1]]=crop
            cv2.putText(tile,o['id'],(3,16),0,.43,(255,255,255),1);cv2.putText(tile,f'load640={o["loaded_height640"]:.1f} src={o["source_height640"]:.1f}',(3,219),0,.36,(255,255,255),1);tiles.append(tile)
        for start in range(0,len(tiles),20):
            group=tiles[start:start+20]+[np.zeros((225,280,3),np.uint8)]*(20-len(tiles[start:start+20]))
            cv2.imwrite(str(out/f'{role}-sheet-{start//20}.jpg'),np.vstack([np.hstack(group[i:i+4]) for i in range(0,20,4)]))
    boards=[]
    for index,parent in enumerate(lock['parent_sample']):
        meta=j['parents'][parent];im=source_frame(root,meta);covered=meta['units']
        for ui in covered:
            unit=j['units'][ui];a,b,c,d=unit['roi'];cv2.rectangle(im,(a,b),(c,d),(255,255,0),1)
        for ob in j['objects']:
            if ob['parent']!=parent:continue
            a,b,c,d=map(int,ob['parent_xyxy']);cv2.rectangle(im,(a,b),(c,d),(0,255,0),1)
        cv2.imwrite(str(out/f'parent-{index}.jpg'),im)
        tile=np.full((385,640,3),20,np.uint8);tile[25:]=cv2.resize(im,(640,360));cv2.putText(tile,f'parent-{index} '+meta['family'],(3,18),0,.43,(255,255,255),1);boards.append(tile)
    for start in range(0,len(boards),6):
        group=boards[start:start+6]+[np.zeros((385,640,3),np.uint8)]*(6-len(boards[start:start+6]))
        cv2.imwrite(str(out/f'parent-sheet-{start//6}.jpg'),np.vstack([np.hstack(group[i:i+2]) for i in range(0,6,2)]))


def validate_review(j,lock,review):
    for key in ['independently_validated','labels_modified','training_performed','sampling_changed','test_inference_performed','heldout_inference_performed']:
        if review[key] is not False:raise ValueError('Unsupported acceptance/change claim')
    selected=set(lock['object_sample']);rows=review['objects'];byid={o['id']:o for o in j['objects']}
    if len(rows)!=len(selected) or {r['id'] for r in rows}!=selected:raise ValueError('Incomplete/duplicate object sample')
    for r in rows:
        o=byid[r['id']]
        if any(r[k]!=o[k] for k in ['id','role','parent','image_sha256','label_sha256','label_id','xyxy']):
            raise ValueError('Frozen object evidence changed')
        if r['independent_status']!='pending' or r['review_status']!='agent_rechecked':raise ValueError('Independent approval not supplied')
        if not r['shirt_appearance'] or not r['location'] or not r['note']:raise ValueError('Explicit visual attributes required')
        if r['role']=='goalkeeper' and r['pose'] not in {'upright','low_or_crouched','uncertain_or_clipped'}:raise ValueError('Invalid keeper pose')
    if len(review['parents'])!=len(lock['parent_sample']) or {r['parent'] for r in review['parents']}!=set(lock['parent_sample']):
        raise ValueError('Incomplete/duplicate parent sample')
    for r in review['parents']:
        parent=j['parents'][r['parent']]
        if r['family']!=parent['family'] or r['unit_ids']!=parent['units']:
            raise ValueError('Frozen parent/ROI union changed')
        if r['review_status']!='agent_sample_reviewed' or not r['coverage_note'] or not r['outside_actor_rule']:
            raise ValueError('Explicit parent coverage review required')
    cases=review['label_proposals']
    if len(cases)!=5 or {c['review_id'] for c in cases}!={'keeper-14','keeper-20','keeper-57','keeper-66','referee-120'}:
        raise ValueError('Exactly five locked suspect cases required')
    for c in cases:
        if c['independent_status']!='pending' or c['applied'] is not False or c['benchmark_excluded'] is not False:
            raise ValueError('Proposal cannot be applied/accepted in this task')
        if c['proposal'] not in {'keep','relabel','add_label','quarantine','insufficient_evidence'} or not c['reason']:
            raise ValueError('Invalid proposal')
        if c['proposal'] in {'keep','relabel'}:
            old=c['old_label_line'].split();new=c['proposed_label_line'].split()
            if old[1:]!=new[1:] or new[0]!=str(NAMES.index(c['proposed_role'])):
                raise ValueError('Class-only proposal changed geometry/role')
        elif c['proposal']=='add_label':
            if c['label_id'] is not None or c['old_label_line'] is not None or c['old_role'] is not None:
                raise ValueError('Addition already has GT')
            if c.get('geometry_status')!='manual_draft_requires_independent_adjustment':
                raise ValueError('Addition geometry is only a draft')
        elif c['proposal']=='insufficient_evidence' and c['proposed_label_line'] is not None:
            raise ValueError('Insufficient evidence cannot provide replacement GT')
    return {r['id']:r for r in rows}


def group_counts(objects):
    return {'unit_boxes':len(objects),'parent_frames':len({o['parent'] for o in objects}),
            'families':dict(Counter(o['family'] for o in objects)),
            'box_exposures':sum(o['exposures'] for o in objects)}


def summarize(root):
    import cv2
    out=root/OUT;lock=json.loads((root/LOCK).read_text());review=json.loads((root/REVIEW).read_text())
    j=json.loads(checked(root,OUT+'/inventory.json',lock['inventory_sha256']).read_text())
    if digest(root/LOCK)!=review['plan_sha256'] or lock['inventory_sha256']!=review['inventory_sha256']:
        raise ValueError('Review lock changed')
    plan,p,m,dataset=load_plan(root)
    if j['manifest_sha256']!=plan['manifest_sha256'] or review['manifest_sha256']!=j['manifest_sha256']:
        raise ValueError('Dataset binding changed')
    manual=validate_review(j,lock,review)
    attrs={}
    for ob in j['objects']:
        attrs[ob['id']]=manual.get(ob['id']) or ({'shirt_appearance':ob['prior_visual']['shirt_appearance'],
            'location':ob['prior_visual']['context'],'pose':'not_reviewed','review_status':'inherited_v10_not_rechecked'} if ob['prior_visual'] else
            {'shirt_appearance':'not_reviewed','location':'not_reviewed','pose':'not_reviewed','review_status':'not_reviewed'})
    for row in review['objects']+review['parents']:
        checked(out,row['evidence'],row['evidence_sha256'])
        if row.get('context_evidence'):checked(out,row['context_evidence'],row['context_evidence_sha256'])
    val={r['image']:r for r in m['files'] if r['split']=='val'}
    for c in review['label_proposals']:
        row=val.get(c['image'])
        if not row or any(c[k]!=row[k] for k in ['image_sha256','label_sha256']):raise ValueError('Case source changed/not val')
        checked(out,c['evidence'],c['evidence_sha256'])
        labels=(dataset/row['label']).read_text().splitlines()
        line=labels[c['label_id']] if c['label_id'] is not None else None
        if c['old_label_line']!=line:raise ValueError('Proposal old GT line changed')
        if line and NAMES[int(line.split()[0])]!=c['old_role']:raise ValueError('Old role differs from GT')
    appearances={}
    for role in ['goalkeeper','referee']:
        appearances[role]={}
        for color in sorted({attrs[o['id']]['shirt_appearance'] for o in j['objects'] if o['role']==role}):
            subset=[o for o in j['objects'] if o['role']==role and attrs[o['id']]['shirt_appearance']==color]
            appearances[role][color]={**group_counts(subset),'small_source640':group_counts([o for o in subset if o['source_height640']<24])}
    sizes={}
    for role in NAMES:
        subset=[o for o in j['objects'] if o['role']==role];sizes[role]={}
        for scope in ['loaded','source']:
            for size in [640,1280]:
                sizes[role][scope+str(size)]={'unit_boxes':dict(Counter(size_bin(o[f'{scope}_height{size}']) for o in subset)),
                    'box_exposures':dict(sum((Counter({size_bin(o[f'{scope}_height{size}']):o['exposures']}) for o in subset),Counter()))}
    dark=[o for o in j['objects'] if o['role']=='referee' and attrs[o['id']]['shirt_appearance']=='dark']
    far=[o for o in dark if attrs[o['id']]['location']=='far_touchline']
    gks=[o for o in j['objects'] if o['role']=='goalkeeper']
    upright_small=[o for o in gks if attrs[o['id']]['pose']=='upright' and o['source_height640']<24]
    players=[o for o in j['objects'] if o['id'] in set(lock['player_sample'])]
    families={}
    for family in sorted({u['family'] for u in j['units']}):
        units=[u for u in j['units'] if u['family']==family];obs=[o for o in j['objects'] if o['family']==family]
        families[family]={'parent_frames':len({u['parent'] for u in units}),'units':len(units),'image_exposures':sum(u['exposures'] for u in units),
             'unit_boxes':dict(Counter(o['role'] for o in obs)),
             'box_exposures':dict(sum((Counter({o['role']:o['exposures']}) for o in obs),Counter()))}
    summary={'kind':'role_coverage_review_summary_v14','manifest_sha256':j['manifest_sha256'],'inventory_sha256':digest(out/'inventory.json'),
       'review_plan_sha256':digest(root/LOCK),'review_sha256':digest(root/REVIEW),'image_exposures':sum(u['exposures'] for u in j['units']),
       'pixel_label_units':len(j['units']),'parent_frames':len(j['parents']),'scene_families':len(families),
       'unit_boxes':dict(Counter(o['role'] for o in j['objects'])),'parent_spatial_clusters':dict(Counter(c['role'] for c in j['clusters'])),
       'box_exposures':dict(sum((Counter({o['role']:o['exposures']}) for o in j['objects']),Counter())),
       'negative_units':sum(not u['objects'] for u in j['units']),'negative_exposures':sum(u['exposures'] for u in j['units'] if not u['objects']),
       'parent_repeat_histogram':dict(Counter(sum(j['units'][i]['exposures'] for i in meta['units']) for meta in j['parents'].values())),
       'families':families,'sizes':sizes,'appearance':appearances,
       'keeper_pose_counts':dict(Counter(attrs[o['id']]['pose'] for o in gks)),
       'upright_small_source640':group_counts(upright_small),
       'upright_small_colors':{color:group_counts([o for o in upright_small if attrs[o['id']]['shirt_appearance']==color]) for color in sorted({attrs[o['id']]['shirt_appearance'] for o in upright_small})},
       'dark_referee':{**group_counts(dark),'locations':dict(Counter(attrs[o['id']]['location'] for o in dark))},
       'dark_far_referee':{**group_counts(far),'ids':[o['id'] for o in far],
           'source_size640':dict(Counter(size_bin(o['source_height640']) for o in far)),
           'loaded_size640':dict(Counter(size_bin(o['loaded_height640']) for o in far)),
           'source_size1280':dict(Counter(size_bin(o['source_height1280']) for o in far)),
           'source_prefixes':dict(Counter(Path(o['image']).name.split('_')[0] for o in far))},
       'visual_sample':{'objects':len(manual),'parents':len(review['parents']),'units':sum(len(p['unit_ids']) for p in review['parents']),
           'player_sample':group_counts(players),'player_colors':dict(Counter(attrs[o['id']]['shirt_appearance'] for o in players)),
           'player_source640_bins':dict(Counter(size_bin(o['source_height640']) for o in players)),
           'player_loaded640_bins':dict(Counter(size_bin(o['loaded_height640']) for o in players)),
           'unreviewed_parent_count':len(j['parents'])-len(review['parents']),
           'other_referee_color_inherited_not_rechecked':sum(o['role']=='referee' and o['id'] not in manual for o in j['objects'])},
       'crop_magnification':{role:group_counts([o for o in j['objects'] if o['role']==role and o['source_height640']<24 and o['loaded_height640']>=48]) for role in NAMES},
       'duplicate_candidates_iou_gt90':j['duplicate_candidates_iou_gt90'],
       'case_proposals':review['label_proposals'],'independently_validated':False,'labels_modified':False,'training_performed':False,'sampling_changed':False,
       'limitations':lock['scope']}
    fields=['id','role','parent','family','image','image_sha256','label_sha256','unit_id','label_id','xyxy','parent_xyxy','roi','exposures','loaded_height640','loaded_height1280','source_height640','source_height1280','shirt_appearance','pose','location','review_status','evidence','evidence_sha256']
    with (out/'train-objects.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for o in j['objects']:w.writerow({k:o.get(k,attrs[o['id']].get(k)) for k in fields})
    with (out/'label-proposals.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['review_id','source_image_path','image_sha256','label_id','old_label_line','old_role','proposal','proposed_role','proposed_xyxy','proposed_label_line','reason','independent_status','applied','benchmark_excluded','evidence']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for c in review['label_proposals']:w.writerow({k:c.get(k) for k in fields})
    write_json(out/'summary.json',summary);write_json(root/'docs/fixtures/role_coverage_review_summary_v14.json',summary)
    print(json.dumps({k:summary[k] for k in ['unit_boxes','box_exposures','keeper_pose_counts','upright_small_colors','dark_far_referee','visual_sample','crop_magnification']},indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['inventory','summarize'])
    action=parser.parse_args().action
    {'inventory':inventory,'summarize':summarize}[action](Path(__file__).resolve().parents[2])
