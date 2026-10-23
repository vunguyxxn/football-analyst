"""Prepare an offline, unlabelled human review packet from a pinned video."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[2]


def workspace_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Paths must stay inside the project")
    return path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(plan_path, output):
    plan = json.loads(workspace_path(plan_path).read_text(encoding='utf-8'))
    output = workspace_path(output)
    if output.exists():
        raise ValueError("Use a new output directory; existing annotations are never overwritten")
    source = workspace_path(plan['video'])
    for path, expected in ((source, plan['video_sha256']),
                           (workspace_path(plan['raw_video']), plan['raw_sha256'])):
        if digest(path) != expected:
            raise ValueError(f"Source hash mismatch: {path.name}")
    frames = [f for clip in plan['clips'] for f in clip['frames']]
    if not frames or len(frames) != len(set(frames)):
        raise ValueError("Need unique sample frames")
    for clip in plan['clips']:
        if not clip['id'].isascii() or not clip['id'].replace('_', '').isalnum():
            raise ValueError("Invalid clip ID")
        if not (0 <= clip['start_frame'] < clip['end_frame_exclusive']):
            raise ValueError("Invalid clip range")
        if any(not isinstance(f, int) or not clip['start_frame'] <= f < clip['end_frame_exclusive']
               for f in clip['frames']):
            raise ValueError("Sample outside clip range")
    if len({c['id'] for c in plan['clips']}) != len(plan['clips']):
        raise ValueError("Duplicate clip ID")
    cap = cv2.VideoCapture(str(source))
    writers = {}
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        size = [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        end = max(c['end_frame_exclusive'] for c in plan['clips'])
        if not cap.isOpened() or abs(fps - plan['fps']) > 1e-6 or size != plan['image_size'] or end > total:
            raise ValueError("Video metadata/range does not match plan")
        raw_cap = cv2.VideoCapture(str(workspace_path(plan['raw_video'])))
        try:
            if (not raw_cap.isOpened() or plan['raw_frame_offset'] < 0
                    or abs(raw_cap.get(cv2.CAP_PROP_FPS) - fps) > 1e-6
                    or plan['raw_frame_offset'] + total > raw_cap.get(cv2.CAP_PROP_FRAME_COUNT)):
                raise ValueError("Raw video offset/fps does not match plan")
        finally:
            raw_cap.release()
        output.mkdir(parents=True)
        (output / 'frames').mkdir()
        (output / 'clips').mkdir()
        samples = set(frames)
        hashes = {}
        counts = {c['id']: 0 for c in plan['clips']}
        for clip in plan['clips']:
            writer = cv2.VideoWriter(str(output / 'clips' / f"{clip['id']}.mp4"),
                                    cv2.VideoWriter_fourcc(*'mp4v'), fps, tuple(size))
            writers[clip['id']] = writer
            if not writer.isOpened():
                raise RuntimeError("Video writer could not open")
        # One sequential decode, only a single full-resolution frame in RAM.
        for frame in range(end):
            ok, picture = cap.read()
            if not ok:
                raise RuntimeError(f"Decode failed at frame {frame}; packet incomplete")
            if frame in samples:
                target = output / 'frames' / f'frame_{frame:06d}.png'
                if not cv2.imwrite(str(target), picture):
                    raise RuntimeError("Image write failed")
                hashes[frame] = digest(target)
            for clip in plan['clips']:
                if clip['start_frame'] <= frame < clip['end_frame_exclusive']:
                    writers[clip['id']].write(picture)
                    counts[clip['id']] += 1
    finally:
        cap.release()
        for writer in writers.values():
            writer.release()
    entries = []
    for clip in sorted(plan['clips'], key=lambda c: c['priority']):
        for frame in clip['frames']:
            entries.append({'clip': clip['id'], 'label': clip['label'], 'clean_frame': frame,
                            'raw_frame': frame + plan['raw_frame_offset'], 'time_s': frame / fps,
                            'raw_time_s': (frame + plan['raw_frame_offset']) / fps,
                            'image': f'frames/frame_{frame:06d}.png', 'image_sha256': hashes[frame],
                            'metric_scope': clip['metric_scope'], 'reviewed': False, 'annotations': []})
    packet = {'version': 1, 'packet_id': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
              'plan': plan, 'reviewer': '', 'frames': entries,
              'clips': [{**c, 'file': f"clips/{c['id']}.mp4", 'frame_count': counts[c['id']],
                         'sha256': digest(output / 'clips' / f"{c['id']}.mp4")} for c in plan['clips']],
              'status': 'pending_human_annotation', 'source_total_frames': total}
    payload = json.dumps(packet, ensure_ascii=False, allow_nan=False)
    (output / 'manifest.json').write_text(payload, encoding='utf-8')
    template = Path(__file__).with_name('video_review.html').read_text(encoding='utf-8')
    # Embedded JSON is data, not executable markup (including malicious labels).
    html = template.replace('__PACKET_JSON__', payload.replace('<', '\\u003c').replace('&', '\\u0026'))
    (output / 'review.html').write_text(html, encoding='utf-8')
    with (output / 'review_frames.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        fields = ['clip','clean_frame','raw_frame','time_s','raw_time_s','image','metric_scope','reviewed']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(entries)
    (output / 'annotations_template.csv').write_text(
        'clip,clean_frame,kind,entity_id,team,visibility,image_x_px,image_y_px,pitch_x_m,pitch_y_m,reviewer,note\n',
        encoding='utf-8-sig')
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', default='docs/fixtures/video_review_plan.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    packet = prepare(args.plan, args.output)
    print(json.dumps({'frames': len(packet['frames']), 'clips': len(packet['clips']),
                      'output': str(workspace_path(args.output)), 'status': packet['status']}))


if __name__ == '__main__':
    main()
