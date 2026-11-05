"""Val1280-only v11/v14 error audit, immutable scoring and bounded raw diagnostics."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from backend.cv.audit_role_errors_v11 import fp_transitions, keeper_false_positives
from backend.cv.audit_role_regressions import explain, raw_evidence, raw_head, transition
from backend.cv.compare_role_models import frame_confusion, operating_metrics
from backend.cv.evaluate_role_detector import checked, digest, iou, match
from backend.cv.finetune_roles import setup, write_json
from backend.cv.prepare_role_dataset import NAMES
from backend.cv.role_distribution import size_bin
from backend.cv.run_role_training_v14 import load_plan

OUT = 'data/processed/role_error_audit_v14'
REVIEW = 'docs/fixtures/role_error_audit_review_v14.json'


def replay(frames, expected):
    totals = {v:[Counter(),Counter()] for v in ['v11','v14']}
    seen = set()
    for frame in frames:
        if frame.get('split') != 'val' or str(frame.get('match_id')) == '128057' or frame['image'] in seen:
            raise ValueError('Only unique validation frames permitted')
        seen.add(frame['image'])
        for v in totals:
            counts,extras = frame_confusion(frame['labels'],frame['predictions'][v])
            totals[v][0].update(counts);totals[v][1].update(extras)
    result = {v:{**operating_metrics(*counts),'frames':len(frames)} for v,counts in totals.items()}
    for v,value in result.items():
        if any(value[k] != expected[v][k] for k in ['classes','confusion','unmatched_predictions','frames']):
            raise ValueError('All-class validation replay differs: '+v)
    return result


def load_inputs(root):
    plan,p,m,dataset = load_plan(root)
    rp = root/'docs/fixtures/role_sources_training_result_v14.json'
    result = json.loads(rp.read_text())
    if (result['protocol_sha256'],result['manifest_sha256']) != (plan['protocol_sha256'],plan['manifest_sha256']):
        raise ValueError('Training result binding changed')
    local = root/plan['comparison_output']/'result.json'
    if digest(local) != digest(rp):
        raise ValueError('Published/local evaluation differ')
    checked(root,plan['comparison_output']+'/validation-before-test.json',result['validation_before_test_sha256'])
    specs = {v:result['weights'][v] for v in ['v11','v14']}
    for spec in specs.values():checked(root,spec['path'],spec['sha256'])
    old_summary = json.loads((root/'docs/fixtures/role_error_audit_summary_v11.json').read_text())
    old_audit = json.loads(checked(root,'data/processed/role_error_audit_v11/result.json',old_summary['audit_result_sha256']).read_text())
    old_review = json.loads(checked(root,'docs/fixtures/role_error_audit_review_v11.json',old_summary['review_packet_sha256']).read_text())
    if old_audit['weights']['v11']['sha256'] != specs['v11']['sha256']:
        raise ValueError('Cached v11 weights differ')
    cache_path = root/'data/processed/role_error_audit_v11/predictions.json'
    cached = json.loads(cache_path.read_text())
    if len(cached)!=128 or len({f['image'] for f in cached})!=128:
        raise ValueError('Incomplete cache')
    return plan,p,m,dataset,result,specs,old_audit,old_review,cached,cache_path


def collect(root):
    import cv2
    plan,p,m,dataset,result,specs,old,old_review,cached,cache_path = load_inputs(root)
    output = root/OUT
    if output.exists():raise ValueError('New audit directory required')
    cache = {f['image']:f for f in cached}
    val = [r for r in m['files'] if r['split']=='val']
    if set(cache)!={r['image'] for r in val}:raise ValueError('Cache image coverage changed')
    torch = setup(root)
    from ultralytics import YOLO
    model = YOLO(str(root/specs['v14']['path']))
    if list(model.names.values())!=NAMES:raise ValueError('Class mapping changed')
    frames=[];keepers=[];oldkeepers=[];refs=[];all_gt=[]
    raw_old = {(r['image'],r['label_id']):r for r in old['referee_fn_rows']}
    raw_images=[]
    for item in val:
        image=cv2.imread(str(dataset/item['image']));h,w=image.shape[:2]
        labels=[]
        for index,line in enumerate((dataset/item['label']).read_text().splitlines()):
            c,x,y,bw,bh=map(float,line.split())
            labels.append({'id':index,'role':NAMES[int(c)],'xyxy':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
        prior=cache[item['image']]
        if any(prior[k]!=item[k] for k in ['image_sha256','label_sha256']) or prior['labels']!=labels:
            raise ValueError('Cached labels/image hashes differ')
        pred=model.predict(image,imgsz=1280,conf=.25,iou=.7,max_det=300,device=0,half=False,verbose=False)[0]
        predictions={'v11':prior['predictions']['v11'], 'v14':[{'id':i,'role':NAMES[int(c)],'xyxy':box,'confidence':score} for i,(box,c,score) in enumerate(zip(pred.boxes.xyxy.cpu().tolist(),pred.boxes.cls.cpu().tolist(),pred.boxes.conf.cpu().tolist()))]}
        paired={v:match(labels,predictions[v],box_iou=.5) for v in predictions}
        fps={v:keeper_false_positives(labels,predictions[v],paired[v]) for v in predictions}
        changes,resolved=fp_transitions(fps['v11'],fps['v14'])
        common={k:item[k] for k in ['image','image_sha256','label_sha256']}
        common.update(width=w,height=h)
        paired_old={c['before_fp_index']:i for i,c in enumerate(changes) if c['before_fp_index'] is not None}
        for i,row in enumerate(fps['v11']):
            oldkeepers.append({**common,**row,'transition':'retained_fp' if i in paired_old else 'resolved_fp',
                               'after_fp':fps['v14'][paired_old[i]] if i in paired_old else None,
                               'height_at_640':(row['xyxy'][3]-row['xyxy'][1])*640/max(w,h)})
        for row,change in zip(fps['v14'],changes):
            keepers.append({**common,**row,**change,'before_fp':fps['v11'][change['before_fp_index']] if change['before_fp_index'] is not None else None,
                            'height_at_640':(row['xyxy'][3]-row['xyxy'][1])*640/max(w,h)})
        pending=[]
        for i,label in enumerate(labels):
            before,after=[paired[v][i]['prediction'] for v in ['v11','v14']]
            row={**common,'label_id':i,'role':label['role'],'xyxy':label['xyxy'],'v11':before,'v14':after,
                 'transition':transition(label['role'],before,after),'height_at_640':(label['xyxy'][3]-label['xyxy'][1])*640/max(w,h)}
            row['size_at_640']=size_bin(row['height_at_640'])
            all_gt.append(row)
            if label['role']=='referee':
                refs.append(row)
                old_case=raw_old.get((item['image'],i))
                if old_case:
                    row['raw_v11']=old_case['raw_v11'];row['diagnostic_v11']=old_case['diagnostic']
                if row['transition'] in {'lost','still_wrong'}:pending.append((row,label))
        if pending:
            head=raw_head(model,image,torch);raw_images.append(item['image'])
            for row,label in pending:
                row['raw_v14']=raw_evidence(label,head)
                row['diagnostic_v14']=explain(label,row['v14'],predictions['v14'],row['raw_v14'])
                row['correct_role_candidates']=[{**pr,'matched_iou':iou(label['xyxy'],pr['xyxy']),
                    'assigned_label_id':next((pair['id'] for pair in paired['v14'] if pair['prediction'] and pair['prediction']['id']==pr['id']),None)} for pr in predictions['v14'] if pr['role']=='referee' and iou(label['xyxy'],pr['xyxy'])>=.5]
        frames.append({**common,'split':'val','labels':labels,'predictions':predictions})
    expected={v:result['models'][v]['validation_1280'] for v in specs}
    reproduced=replay(frames,expected)
    output.mkdir(parents=True)
    export_evidence(dataset,output,keepers,oldkeepers,refs)
    audit={'kind':'role_error_audit_v14','protocol_sha256':result['protocol_sha256'],'manifest_sha256':result['manifest_sha256'],
           'comparison_result_sha256':digest(root/'docs/fixtures/role_sources_training_result_v14.json'),'weights':specs,
           'reproduced_all_class_validation':reproduced,'keeper_fp_rows':keepers,'old_keeper_fp_rows':oldkeepers,
           'all_referee_rows':refs,'all_gt_rows':all_gt,'size':1280,'confidence':.25,'nms_iou':.7,'matching_iou':.5,'max_det':300,'half':False,'cross_role_dedup':False,
           'inference':{'v11_postprocessed_reused':128,'v14_postprocessed_new':128,'v14_raw_related_val_images':raw_images,
                        'v11_raw_reused_labels':sum('raw_v11' in r for r in refs),'known_test':False,'match128057':False},
           'cache_sha256':digest(cache_path),'old_audit_sha256':digest(root/'data/processed/role_error_audit_v11/result.json'),
           'training_performed':False,'labels_changed':False,'runtime_changed':False}
    write_json(output/'predictions.json',frames);write_json(output/'result.json',audit)
    export_csv(output,audit)
    print(json.dumps({'keeper_fp':len(keepers),'keeper_transitions':dict(Counter(r['transition'] for r in keepers)),
        'old_keeper_transitions':dict(Counter(r['transition'] for r in oldkeepers)),
        'referee_transitions':dict(Counter(r['transition'] for r in refs)),
        'referee_fn_diagnostics':dict(Counter(r['diagnostic_v14'] for r in refs if 'diagnostic_v14' in r))},indent=2))


def export_evidence(dataset,output,keepers,oldkeepers,refs):
    import cv2
    import numpy as np
    groups=[('keeper',keepers),('oldkeeper',oldkeepers),('referee',refs)]
    images=list(dict.fromkeys(r['image'] for _,rows in groups for r in rows))
    context={name:f'context-{i}.jpg' for i,name in enumerate(images)}
    for kind,rows in groups:
        for i,row in enumerate(rows):
            row['review_id']=f'{kind}-{i}';row['context_path']=context[row['image']]
            image=cv2.imread(str(dataset/row['image']));h,w=image.shape[:2]
            a,b,c,d=map(int,row['xyxy']);x,y=max(0,a-95),max(0,b-75)
            crop=image[y:min(h,d+75),x:min(w,c+95)].copy()
            cv2.rectangle(crop,(a-x,b-y),(c-x,d-y),(0,255,255),1)
            row['crop_path']=row['review_id']+'.jpg'
            cv2.imwrite(str(output/row['crop_path']),crop)
        subsets= [(kind,rows)] if kind!='referee' else [(state+'-referee',[r for r in rows if r['transition']==state]) for state in ['lost','gained','still_wrong','retained']]
        for group,subset in subsets:
            tiles=[]
            for row in subset:
                crop=cv2.imread(str(output/row['crop_path']))
                scale=min(300/crop.shape[1],205/crop.shape[0]);crop=cv2.resize(crop,None,fx=scale,fy=scale)
                tile=np.full((245,310,3),25,np.uint8);tile[23:23+crop.shape[0],:crop.shape[1]]=crop
                cv2.putText(tile,row['review_id']+' '+row['transition'],(2,16),0,.42,(255,255,255),1)
                cv2.putText(tile,f'h640={row["height_at_640"]:.1f}',(2,240),0,.42,(255,255,255),1)
                tiles.append(tile)
            for start in range(0,len(tiles),20):
                batch=tiles[start:start+20]+[np.zeros((245,310,3),np.uint8)]*(20-len(tiles[start:start+20]))
                path=f'{group}-sheet-{start//20}.jpg'
                cv2.imwrite(str(output/path),np.vstack([np.hstack(batch[i:i+4]) for i in range(0,20,4)]))
                for row in subset[start:start+20]:row['sheet_path']=path
    for name,path in context.items():
        image=cv2.imread(str(dataset/name))
        for row in keepers+refs:
            if row['image']!=name:continue
            a,b,c,d=map(int,row['xyxy']);color=(0,0,255) if row['review_id'].startswith('keeper') else (0,255,0)
            cv2.rectangle(image,(a,b),(c,d),color,1)
            cv2.putText(image,row['review_id'],(a,max(12,b-3)),0,.36,color,1)
        cv2.imwrite(str(output/path),image)
    for _,rows in groups:
        for row in rows:
            row['crop_sha256']=digest(output/row['crop_path']);row['context_sha256']=digest(output/row['context_path'])


def export_csv(output,audit):
    fields=['review_id','image','label_id','prediction_id','transition','role','xyxy','score','height_at_640','crop_path','context_path']
    with (output/'audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in audit['keeper_fp_rows']+audit['old_keeper_fp_rows']+audit['all_referee_rows']:
            writer.writerow({k:row.get(k) for k in fields if k not in {'prediction_id','score'}} |
                {'prediction_id':row.get('prediction',{}).get('id'),'score':row.get('prediction',{}).get('confidence')})


def validate_review(audit, review):
    for key in ['training_performed','labels_changed','independently_validated','test_inference_performed','heldout_inference_performed','half','cross_role_dedup']:
        if review[key] is not False:
            raise ValueError('Unsupported review claim/settings')
    for key in ['manifest_sha256','weights','size','confidence','nms_iou','matching_iou','max_det']:
        if review[key] != audit[key]:
            raise ValueError('Review source or thresholds changed')
    groups = [('keeper_fp_rows','keeper_predictions'),('old_keeper_fp_rows','old_keeper_predictions'),('all_referee_rows','referee_labels')]
    for original_key,reviewed_key in groups:
        original={r['review_id']:r for r in audit[original_key]};rows=review[reviewed_key]
        if len(rows)!=len(original) or {r['review_id'] for r in rows}!=set(original):
            raise ValueError('Incomplete/duplicate review coverage')
        for row in rows:
            if any(row.get(k)!=v for k,v in original[row['review_id']].items()):
                raise ValueError('Frozen audit evidence changed')
            if row['review_status']!='agent_reviewed' or not row.get('review_note'):
                raise ValueError('Missing visual review')
            if reviewed_key=='referee_labels':
                if row['location'] not in {'interior','far_touchline','near_touchline','near_touchline_role_uncertain','unknown'} or not row.get('shirt_color'):
                    raise ValueError('Missing/invalid visual attributes')
            elif not row.get('visual_subject'):
                raise ValueError('Missing visual subject')
    return {key:len(review[key]) for _,key in groups}


def summarize(root):
    output=root/OUT
    review=json.loads((root/REVIEW).read_text())
    audit=json.loads(checked(root,OUT+'/result.json',review['audit_result_sha256']).read_text())
    frames=json.loads(checked(root,OUT+'/predictions.json',review['predictions_sha256']).read_text())
    coverage=validate_review(audit,review)
    plan,p,m,dataset,result,specs,old,old_review,cached,cache_path=load_inputs(root)
    if digest(cache_path)!=audit['cache_sha256']:
        raise ValueError('Cached prediction file changed')
    reproduced=replay(frames,{v:result['models'][v]['validation_1280'] for v in specs})
    # Bind reused cache to the published old per-error/per-GT evidence, not totals alone.
    for row,prior in zip(audit['old_keeper_fp_rows'],old['keeper_fp_rows']):
        if any(row[k]!=prior[k] for k in ['image','image_sha256','label_sha256','prediction','xyxy','mechanism']):
            raise ValueError('Old keeper cache evidence differs')
    old_refs={(r['image'],r['label_id']):r for r in old['all_referee_rows']}
    for row in audit['all_referee_rows']:
        prior=old_refs[(row['image'],row['label_id'])]
        if any(row[k]!=prior[k] for k in ['image_sha256','label_sha256','xyxy','v11']):
            raise ValueError('Old referee cache evidence differs')
    for key in ['keeper_predictions','old_keeper_predictions','referee_labels']:
        for row in review[key]:
            checked(output,row['crop_path'],row['crop_sha256'])
            checked(output,row['context_path'],row['context_sha256'])
            if row.get('wide_context_sheet'):checked(output,row['wide_context_sheet'])
            if row.get('extra_detail_path'):checked(output,row['extra_detail_path'],row['extra_detail_sha256'])
    refs=review['referee_labels'];keepers=review['keeper_predictions'];oldkeepers=review['old_keeper_predictions']
    locations={}
    for location in sorted({r['location'] for r in refs}):
        subset=[r for r in refs if r['location']==location]
        locations[location]={'labels':len(subset),'transitions':dict(Counter(r['transition'] for r in subset)),
            'size_bins_at_640':dict(Counter(r['size_at_640'] for r in subset)),
            'fn_diagnostics':dict(Counter(r['diagnostic_v14'] for r in subset if 'diagnostic_v14' in r)),
            'lost_diagnostics':dict(Counter(r['diagnostic_v14'] for r in subset if r['transition']=='lost'))}
    gt_transitions={role:dict(Counter(r['transition'] for r in audit['all_gt_rows'] if r['role']==role)) for role in NAMES}
    frame_map={f['image']:f for f in frames}
    lost_players=[r for r in audit['all_gt_rows'] if r['role']=='player' and r['transition']=='lost']
    player_correct_boxes=sum(any(pr['role']=='player' and iou(pr['xyxy'],r['xyxy'])>=.5 for pr in frame_map[r['image']]['predictions']['v14']) for r in lost_players)
    flags=[{'review_id':r['review_id'],'image':r['image'],'label_id':r.get('flag_label_id',r.get('label_id', (r.get('assigned_label') or {}).get('id'))),
            'flag':r['gt_flag'],'crop_path':r['crop_path'],'context_path':r['context_path']} for key in ['keeper_predictions','old_keeper_predictions','referee_labels'] for r in review[key] if r.get('gt_flag')]
    summary={'kind':'role_error_audit_summary_v14','audit_result_sha256':digest(output/'result.json'),
        'predictions_sha256':digest(output/'predictions.json'),'review_packet_sha256':digest(root/REVIEW),
        'coverage':coverage,'all_class_validation':reproduced,'all_gt_transitions':gt_transitions,
        'keeper_fp_transitions':dict(Counter(r['transition'] for r in keepers)),
        'old_keeper_fp_transitions':dict(Counter(r['transition'] for r in oldkeepers)),
        'keeper_visual_subjects':dict(Counter(r['visual_subject'] for r in keepers)),
        'new_keeper_visual_subjects':dict(Counter(r['visual_subject'] for r in keepers if r['transition']=='new_fp')),
        'keeper_fp_mechanisms':dict(Counter(r['mechanism'] for r in keepers)),
        'referee_locations':locations,'referee_size_transitions':{size:dict(Counter(r['transition'] for r in refs if r['size_at_640']==size)) for size in ['under24','24to48','48plus']},
        'referee_shirt_colors':dict(Counter(r['shirt_color'] for r in refs)),
        'referee_fn_diagnostics':dict(Counter(r['diagnostic_v14'] for r in refs if 'diagnostic_v14' in r)),
        'lost_referee_diagnostics':dict(Counter(r['diagnostic_v14'] for r in refs if r['transition']=='lost')),
        'gained_referee_old_diagnostics':dict(Counter(r['diagnostic_v11'] for r in refs if r['transition']=='gained')),
        'lost_player_destinations':dict(Counter((r['v14'] or {}).get('role','missed') for r in lost_players)),
        'lost_player_with_correct_role_box_still_present':player_correct_boxes,'gt_flags':flags,
        'inference':audit['inference'],'independently_validated':False,'labels_changed':False,'training_performed':False,
        'method':'Exact frozen-label replay. FP association same image, role-blind greedy descending IoU>=0.5, one-to-one, deterministic index tie breaks. No person identity or match independence claim.'}
    fields=['review_id','image','source_image_path','label_id','prediction_id','role','xyxy','score','v11','v14','transition','height_at_640','visual_subject','shirt_color','location','gt_flag','diagnostic_v14','crop_path','context_path']
    with (output/'reviewed-audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for key in ['keeper_predictions','old_keeper_predictions','referee_labels']:
            for row in review[key]:
                data={k:row.get(k) for k in fields}
                data.update(source_image_path=str(dataset/row['image']),label_id=row.get('label_id',(row.get('assigned_label') or {}).get('id')),
                            prediction_id=row.get('prediction',{}).get('id'),role=row.get('role',row.get('prediction',{}).get('role')),
                            score=row.get('prediction',{}).get('confidence'))
                writer.writerow(data)
    write_json(root/'docs/fixtures/role_error_audit_summary_v14.json',summary)
    write_json(output/'summary.json',summary)
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['collect','summarize'])
    action=parser.parse_args().action
    {'collect':collect,'summarize':summarize}[action](Path(__file__).resolve().parents[2])
