"""Package explicit visual draft labels; never represent them as human truth."""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

import cv2

from backend.cv.prepare_video_review import workspace_path, digest


def export(packet_dir, labels_file, output_dir):
    packet_dir, labels_file, output = map(workspace_path, (packet_dir, labels_file, output_dir))
    if output.exists():
        raise ValueError('Use a new output directory; never overwrite previous reviews')
    packet = json.loads((packet_dir / 'manifest.json').read_text(encoding='utf-8'))
    labels = json.loads(labels_file.read_text(encoding='utf-8'))
    if labels['source_sha256'] != packet['plan']['video_sha256']:
        raise ValueError('Source hash mismatch')
    if set(labels['frames']) != {str(f['clean_frame']) for f in packet['frames']}:
        raise ValueError('Labels must cover exactly the packet frames')
    width, height = packet['plan']['image_size']
    landmarks = {l['id']: l for l in packet['plan']['landmarks']}
    images, counts = {}, Counter()
    for frame in packet['frames']:
        key = str(frame['clean_frame'])
        image_file = workspace_path(packet_dir / frame['image'])
        if digest(image_file) != frame['image_sha256']:
            raise ValueError('Image hash mismatch')
        images[key] = image_file
        row = labels['frames'][key]
        annotations = []
        for team, prefix in (('A', 'A'), ('B', 'B'), ('referee', 'R')):
            for item in row.get(team, []):
                identity, x, y = item[:3]
                visibility = item[3] if len(item) == 4 else 'visible'
                annotations.append({'kind': 'player', 'entity_id': f'{prefix}{identity:02d}',
                                    'team': team, 'visibility': visibility,
                                    'image_x_px': x, 'image_y_px': y,
                                    'pitch_x_m': None, 'pitch_y_m': None,
                                    'note': 'Agent visual estimate; local identity tentative.'})
        for name, x, y in row.get('landmarks', []):
            if name not in landmarks:
                raise ValueError('Unknown landmark')
            px, py = landmarks[name]['pitch_xy']
            annotations.append({'kind': 'landmark', 'entity_id': name, 'team': None,
                                'visibility': 'visible', 'image_x_px': x, 'image_y_px': y,
                                'pitch_x_m': px, 'pitch_y_m': py,
                                'note': 'Visual line intersection; metric position assumes 105x68 m.'})
        identities = [(a['kind'], a['entity_id']) for a in annotations]
        if len(identities) != len(set(identities)):
            raise ValueError('Duplicate identity in frame')
        for a in annotations:
            if (a['visibility'] not in ('visible', 'occluded', 'uncertain')
                    or not all(math.isfinite(v) for v in (a['image_x_px'], a['image_y_px']))
                    or not 0 <= a['image_x_px'] < width or not 0 <= a['image_y_px'] < height):
                raise ValueError('Invalid image annotation')
            counts[a['kind']] += 1
            if a['kind'] == 'player':
                counts[a['team']] += 1
                counts[a['visibility']] += 1
        frame.update(annotations=annotations, reviewed=True, human_reviewed=False,
                     review_note=row.get('note', 'All positions are approximate agent visual labels.'))
        # This export lives in a child folder; paths stay portable inside it.
        frame['image'] = '../' + frame['image']
    for clip in packet['clips']:
        clip['file'] = '../' + clip['file']
    packet.update(reviewer='Codex — agent visual review', status='agent_review_not_independent_ground_truth',
                  review_session_id='agent_' + digest(labels_file)[:12],
                  annotation_provenance={'author_type': 'agent', 'independent_ground_truth': False,
                                         'method': 'visual_estimate_from_raw_images',
                                         'note': labels['provenance'], 'labels_sha256': digest(labels_file)})
    if output.parent != packet_dir:
        raise ValueError('Output must be a new child folder of the original packet')
    output.mkdir()
    (output / 'annotated_frames').mkdir()
    for frame in packet['frames']:
        image = cv2.imread(str(images[str(frame['clean_frame'])]))
        if image is None or image.shape[:2] != (height, width):
            raise ValueError('Image dimensions do not match packet')
        for a in frame['annotations']:
            x, y = round(a['image_x_px']), round(a['image_y_px'])
            color = (0, 220, 100) if a['team'] == 'A' else (255, 200, 0)
            if a['kind'] == 'landmark': color = (0, 220, 255)
            elif a['visibility'] != 'visible': color = (60, 60, 255)
            cv2.circle(image, (x, y), 4, color, 2)
            cv2.putText(image, a['entity_id'], (min(x+6, width-130), max(18, y-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)
        cv2.putText(image, 'AGENT DRAFT - NOT INDEPENDENT GROUND TRUTH', (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 210, 255), 2, cv2.LINE_AA)
        target = output / 'annotated_frames' / f"frame_{frame['clean_frame']:06d}.jpg"
        if not cv2.imwrite(str(target), image):
            raise RuntimeError('Could not write annotated preview')
    payload = json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False)
    (output / 'annotations_agent_review.json').write_text(payload, encoding='utf-8')
    html = Path(__file__).with_name('video_review.html').read_text(encoding='utf-8')
    (output / 'review.html').write_text(html.replace('__PACKET_JSON__', payload.replace('<', '\\u003c')),
                                       encoding='utf-8')
    with (output / 'annotations_agent_review.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        fields = ['clip','clean_frame','kind','entity_id','team','visibility','image_x_px','image_y_px',
                  'pitch_x_m','pitch_y_m','reviewer','annotation_author_type','independent_ground_truth','note']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for frame in packet['frames']:
            for a in frame['annotations']:
                writer.writerow({**a,'clip':frame['clip'],'clean_frame':frame['clean_frame'],
                                 'reviewer':packet['reviewer'],'annotation_author_type':'agent',
                                 'independent_ground_truth':False})
    summary = {'status': packet['status'], 'frames_reviewed_by_agent': len(packet['frames']),
               'frames_reviewed_by_human': 0, 'independent_ground_truth': False, 'counts': dict(counts),
               'source_sha256': labels['source_sha256'],
               'limitations': 'Sparse approximate pixel labels; no true metre/speed errors, MOTA or IDF1.'}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--labels', default='docs/fixtures/vid1_11f23eea_agent_review.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.packet, args.labels, args.output), ensure_ascii=False))


if __name__ == '__main__':
    main()
