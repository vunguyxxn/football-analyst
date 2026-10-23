from collections import Counter
from io import StringIO
import json
from types import SimpleNamespace

import numpy as np

from backend.cv.compare_person_video import evaluate_samples, paired_diagnostics, recording_tracker


def test_tracker_recorder_preserves_inputs_results_and_empty_frames():
    class Base:
        def __init__(self, frame_rate):
            self.frame_rate = frame_rate
            self.inputs = []

        def update_with_detections(self, detections):
            self.inputs.append(detections)
            return detections

    stream, samples, counts = StringIO(), {0: None, 1: None}, Counter()
    tracker = recording_tracker(Base, stream, samples, counts)(frame_rate=60)
    populated = SimpleNamespace(xyxy=np.array([[10., 20., 30., 40.]]), tracker_id=np.array([17]))
    empty = SimpleNamespace(xyxy=np.empty((0, 4)), tracker_id=np.array([], dtype=int))
    assert tracker.update_with_detections(populated) is populated
    assert tracker.update_with_detections(empty) is empty
    assert tracker.inputs[0] is populated and tracker.inputs[1] is empty
    assert tracker.frame_rate == 60
    assert samples[0][0]['image_xy'] == [20., 40.]
    assert samples[0][0]['track_id'] == 17 and samples[1] == []
    assert counts == {'frames': 2, 'observations': 1, 'nonempty_frames': 1}
    assert [json.loads(line)['frame'] for line in stream.getvalue().splitlines()] == [0, 1]


def test_sparse_comparison_counts_missing_samples_and_changes_per_model():
    protocol = {'frames': [10, 30, 50], 'sensitivity_gates_px': [8, 12, 20], 'max_sample_gap_frames': 90}
    labels = {'frames': {str(f): {'A': [[1, 100, 100]], 'B': [], 'referee': []} for f in protocol['frames']}}
    samples = {10: [{'image_xy': [101, 100], 'track_id': 1, 'team': 'A'}],
               30: [{'image_xy': [102, 100], 'track_id': 2, 'team': 'A'}], 50: []}
    trials = evaluate_samples(labels, samples, protocol)
    assert [t['gate_px'] for t in trials] == [8, 12, 20]
    for trial in trials:
        summary = trial['summary']
        assert summary['visible_label_observations'] == 3
        assert summary['matched_observations'] == 2
        assert summary['sampled_identity_intervals'] == 1
        assert len(summary['apparent_sampled_identity_changes']) == 1
        assert trial['frames'][-1]['unmatched_visible_labels'][0]['identity'] == 'A01'


def test_paired_identity_comparison_uses_same_label_intervals_not_numeric_ids():
    protocol = {'frames': [10, 30, 50], 'sensitivity_gates_px': [12], 'max_sample_gap_frames': 90}
    def frame(index, identities):
        return {'frame': index, 'matches': [dict(identity=i, track_id=t, distance_px=2., ambiguous=False)
                                           for i, t in identities]}
    def run(frames):
        return {'evaluation': [{'gate_px': 12, 'frames': frames}]}
    baseline = run([frame(10, [('A01', 1), ('A02', 2)]), frame(30, [('A01', 3), ('A02', 2)]),
                    frame(50, [('A01', 3), ('A02', 4)])])
    candidate = run([frame(10, [('A01', 50)]), frame(30, [('A01', 50)]), frame(50, [])])
    result = paired_diagnostics({'baseline': baseline, 'finetuned': candidate}, protocol)[0]
    assert result['common_sampled_identity_intervals'] == 1
    assert len(result['apparent_identity_changes']['baseline']) == 1
    assert result['apparent_identity_changes']['finetuned'] == []
    assert result['common_unambiguous_pixel_errors']['baseline']['count'] == 2
