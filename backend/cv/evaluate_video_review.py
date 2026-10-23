"""Sparse pixel associations against agent draft labels; not MOT ground truth."""
import argparse
from collections import Counter
import hashlib
import json
import math
from statistics import mean, median

from backend.cv.prepare_video_review import workspace_path


def canonical_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def assign_points(reference, predictions, gate):
    """Max-cardinality, min-total-distance gated bipartite matching.

    Successive shortest augmenting paths include reverse edges so a close
    greedy match cannot block a second valid person. No team/ID enters cost.
    """
    if not math.isfinite(gate) or gate <= 0:
        raise ValueError('Gate must be positive and finite')
    n, m = len(reference), len(predictions)
    sink = n + m + 1
    graph = [[] for _ in range(sink + 1)]

    def edge(a, b, cost):
        forward = [b, len(graph[b]), 1, cost]
        backward = [a, len(graph[a]), 0, -cost]
        graph[a].append(forward)
        graph[b].append(backward)
        return forward

    for i in range(n): edge(0, 1 + i, 0.)
    for j in range(m): edge(1 + n + j, sink, 0.)
    links = {}
    for i, a in enumerate(reference):
        for j, b in enumerate(predictions):
            distance = math.hypot(a[0] - b[0], a[1] - b[1])
            if distance <= gate:
                links[i, j] = (edge(1 + i, 1 + n + j, distance), distance)
    while True:
        distances, previous = [math.inf] * len(graph), [None] * len(graph)
        distances[0] = 0.
        # Bellman-Ford supports negative-cost reverse edges after reassignment.
        for _ in range(len(graph) - 1):
            changed = False
            for a, edges in enumerate(graph):
                for k, (b, _, capacity, cost) in enumerate(edges):
                    if capacity and distances[a] + cost < distances[b] - 1e-12:
                        distances[b] = distances[a] + cost
                        previous[b] = (a, k)
                        changed = True
            if not changed: break
        if previous[sink] is None: break
        node = sink
        while node:
            a, k = previous[node]
            arc = graph[a][k]
            arc[2] -= 1
            graph[node][arc[1]][2] += 1
            node = a
    return [(i, j, distance) for (i, j), (arc, distance) in links.items() if not arc[2]]


def point_labels(row):
    result = []
    for team, prefix in (('A', 'A'), ('B', 'B'), ('referee', 'R')):
        for item in row.get(team, []):
            identity, x, y = item[:3]
            visibility = item[3] if len(item) == 4 else 'visible'
            result.append({'identity': f'{prefix}{identity:02d}', 'team': team,
                           'xy': [x, y], 'visibility': visibility})
    return result


def evaluate_frame(labels, predictions, gate):
    visible = [a for a in labels if a['visibility'] == 'visible']
    excluded = [a for a in labels if a['visibility'] != 'visible']
    distances = [[math.dist(a['xy'], p['image_xy']) for p in predictions] for a in visible]
    assignments = assign_points([a['xy'] for a in visible], [p['image_xy'] for p in predictions], gate)
    used_refs, used_preds = set(), set()
    matches = []
    for i, j, distance in assignments:
        used_refs.add(i); used_preds.add(j)
        ambiguous = (sum(d <= gate for d in distances[i]) > 1
                     or sum(row[j] <= gate for row in distances) > 1
                     or any(math.dist(a['xy'], predictions[j]['image_xy']) <= gate for a in excluded))
        matches.append({'identity': visible[i]['identity'], 'label_team': visible[i]['team'],
                        'track_id': predictions[j]['track_id'], 'predicted_team': predictions[j]['team'],
                        'distance_px': distance, 'ambiguous': ambiguous})
    ignored = [p['track_id'] for j, p in enumerate(predictions) if j not in used_preds and
               any(math.dist(a['xy'], p['image_xy']) <= gate for a in excluded)]
    return {'visible_labels': len(visible), 'excluded_labels': len(excluded),
            'predictions': len(predictions), 'matches': matches,
            'unmatched_visible_labels': [{'identity': a['identity'],
                                          'nearest_distance_px': min(distances[i]) if predictions else None}
                                         for i, a in enumerate(visible) if i not in used_refs],
            'predictions_near_excluded_labels': ignored,
            'unmatched_prediction_ids': [p['track_id'] for j, p in enumerate(predictions)
                                         if j not in used_preds and p['track_id'] not in ignored]}


def error_stats(values):
    if not values:
        return {'count': 0, 'mean_px': None, 'median_px': None, 'p95_px': None, 'rmse_px': None}
    ordered = sorted(values)
    x = .95 * (len(values) - 1)
    lo, hi = math.floor(x), math.ceil(x)
    return {'count': len(values), 'mean_px': mean(values), 'median_px': median(values),
            'p95_px': ordered[lo] + (ordered[hi] - ordered[lo]) * (x - lo),
            'rmse_px': math.sqrt(mean(v*v for v in values))}


def summarize(frames, max_gap):
    matches = [m for f in frames for m in f['matches']]
    unambiguous = [m for m in matches if not m['ambiguous']]
    role_pairs = Counter(f"{m['label_team']}->{m['predicted_team']}" for m in unambiguous)
    changes, disappearances, intervals = [], [], 0
    for previous, current in zip(frames, frames[1:]):
        if previous['clip'] != current['clip'] or current['frame'] - previous['frame'] > max_gap:
            continue
        before = {m['identity']: m for m in previous['matches'] if not m['ambiguous']}
        after = {m['identity']: m for m in current['matches'] if not m['ambiguous']}
        for identity in sorted(before.keys() & after.keys()):
            intervals += 1
            if before[identity]['track_id'] != after[identity]['track_id']:
                changes.append({'identity': identity, 'previous_frame': previous['frame'],
                                'frame': current['frame'], 'from_track': before[identity]['track_id'],
                                'to_track': after[identity]['track_id']})
        for label in current['unmatched_visible_labels']:
            if label['identity'] in before:
                disappearances.append({'identity': label['identity'], 'previous_frame': previous['frame'],
                                       'frame': current['frame']})
    visible = sum(f['visible_labels'] for f in frames)
    return {'visible_label_observations': visible,
            'excluded_label_observations': sum(f['excluded_labels'] for f in frames),
            'prediction_observations': sum(f['predictions'] for f in frames),
            'matched_observations': len(matches), 'unambiguous_matched_observations': len(unambiguous),
            'gated_association_fraction': len(matches)/visible if visible else None,
            'pixel_discrepancy_matched_only': error_stats([m['distance_px'] for m in matches]),
            'pixel_discrepancy_unambiguous_only': error_stats([m['distance_px'] for m in unambiguous]),
            'unmatched_predictions_near_excluded_labels': sum(len(f['predictions_near_excluded_labels']) for f in frames),
            'other_unmatched_prediction_observations': sum(len(f['unmatched_prediction_ids']) for f in frames),
            'unambiguous_role_pairs': dict(sorted(role_pairs.items())),
            'sampled_identity_intervals': intervals, 'apparent_sampled_identity_changes': changes,
            'sample_match_disappearances': disappearances}


def run(protocol_path, output):
    output = workspace_path(output)
    if output.exists(): raise ValueError('Use a new report file')
    config = json.loads(workspace_path(protocol_path).read_text(encoding='utf-8'))
    labels = json.loads(workspace_path(config['labels']).read_text(encoding='utf-8'))
    predictions = json.loads(workspace_path(config['predictions']).read_text(encoding='utf-8'))
    for data, name in ((labels, 'labels'), (predictions, 'predictions')):
        if canonical_hash(data) != config[f'{name}_canonical_sha256']:
            raise ValueError(f'{name} canonical hash mismatch')
        if data['source_sha256'] != config['source_sha256']:
            raise ValueError('Video source mismatch')
    expected = config['frames']
    if not expected or expected != sorted(set(expected)):
        raise ValueError('Sample frames must be unique and increasing')
    if config['primary_gate_px'] not in config['sensitivity_gates_px'] or config['max_sample_gap_frames'] <= 0:
        raise ValueError('Invalid primary gate/sample gap')
    samples = {f['frame']: f for f in predictions['frames']}
    if len(samples) != len(predictions['frames']) or set(samples) != set(expected):
        raise ValueError('Frozen prediction frames do not match protocol')
    width, height = predictions['image_size']
    for frame in expected:
        refs = point_labels(labels['frames'][str(frame)])
        if len({a['identity'] for a in refs}) != len(refs): raise ValueError('Duplicate label ID')
        for a in refs:
            if (a['visibility'] not in ('visible', 'occluded', 'uncertain')
                    or not all(math.isfinite(v) for v in a['xy'])
                    or not 0 <= a['xy'][0] < width or not 0 <= a['xy'][1] < height):
                raise ValueError('Invalid reference pixel')
        for stage in ('raw', 'filtered'):
            rows = samples[frame][stage]
            if len({r['track_id'] for r in rows}) != len(rows): raise ValueError('Duplicate prediction ID')
            if any(len(r['image_xy']) != 2 or not all(math.isfinite(v) for v in r['image_xy'])
                   or r['team'] not in ('A','B','referee','unknown') for r in rows):
                raise ValueError('Invalid prediction')
    trials = []
    for gate in config['sensitivity_gates_px']:
        stages = {}
        for stage in ('raw', 'filtered'):
            frames = [{'frame': f, 'clip': samples[f]['clip'],
                       **evaluate_frame(point_labels(labels['frames'][str(f)]), samples[f][stage], gate)}
                      for f in expected]
            stages[stage] = {'frames': frames, 'summary': summarize(frames, config['max_sample_gap_frames'])}
        common_errors = {'raw': [], 'filtered': []}
        for raw, filtered in zip(stages['raw']['frames'], stages['filtered']['frames']):
            a = {m['identity']: m for m in raw['matches'] if not m['ambiguous']}
            b = {m['identity']: m for m in filtered['matches'] if not m['ambiguous']}
            for identity in a.keys() & b.keys():
                if a[identity]['track_id'] == b[identity]['track_id']:
                    common_errors['raw'].append(a[identity]['distance_px'])
                    common_errors['filtered'].append(b[identity]['distance_px'])
        trials.append({'gate_px': gate, **stages,
                       'same_frame_identity_track_unambiguous': {k: error_stats(v) for k,v in common_errors.items()}})
    report = {'scope': config['scope'], 'annotation_author_type': 'agent', 'independent_ground_truth': False,
              'configuration': config, 'frozen_prediction_audit': predictions['audit'],
              'warning': 'Gated matched-only pixel diagnostics on sparse approximate agent labels; association fraction is not detector recall. Apparent sampled ID changes are not MOT ID switches. No metre/speed validation.',
              'trials': trials}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default='docs/fixtures/video_review_evaluation.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = run(args.protocol, args.output)
    primary = next(t for t in report['trials'] if t['gate_px'] == report['configuration']['primary_gate_px'])
    print(json.dumps({stage: primary[stage]['summary'] for stage in ('raw','filtered')}, ensure_ascii=False))


if __name__ == '__main__': main()
