"""Experimental local detector queries near a recently observed ball; no imputation."""
import math

import numpy as np


def contact_crops(frame, people, history, frame_index, fps):
    if not history or frame_index - history[-1][0] > max(1, round(fps * .15)):
        return []
    height, width = frame.shape[:2]
    last = history[-1][1]
    eligible = []
    for person in people:
        left, top, right, bottom = person["xyxy"]
        size = bottom - top
        if size < 12:
            continue
        foot = np.array([(left + right) / 2, bottom])
        distance = np.linalg.norm(foot - last)
        if distance <= max(70, size * 1.5):
            eligible.append((distance, foot, size))
    crops = []
    for _, foot, size in sorted(eligible, key=lambda item: item[0])[:2]:
        center = (foot + last) / 2
        radius = max(80, min(160, size * 1.25))
        x1, y1 = max(0, math.floor(center[0] - radius)), max(0, math.floor(center[1] - radius))
        x2, y2 = min(width, math.ceil(center[0] + radius)), min(height, math.ceil(center[1] + radius))
        if min(x2 - x1, y2 - y1) >= 32:
            crops.append((frame[y1:y2, x1:x2], x1, y1))
    return crops


def refine_candidates(model, frame, people, history, frame_index, fps, device):
    crops = contact_crops(frame, people, history, frame_index, fps)
    if not crops:
        return [], 0
    # Separate ball-only weights: class0 here is ball, never person.
    results = model.predict([crop for crop, _, _ in crops], imgsz=640, conf=.25, device=device, verbose=False)
    candidates = []
    for result, (_, x, y) in zip(results, crops):
        for box, score in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()):
            candidates.append({"xyxy": (box + [x, y, x, y]).tolist(), "score": float(score), "proposal": "contact_crop"})
    return candidates, len(crops)


def merge_candidates(candidates):
    """Keep the strongest duplicate box before temporal ambiguity gating."""
    kept = []
    for candidate in sorted(candidates, key=lambda item: -item["score"]):
        box = np.asarray(candidate["xyxy"], dtype=float)
        duplicate = False
        for other in kept:
            other_box = np.asarray(other["xyxy"], dtype=float)
            intersection = np.maximum(0, np.minimum(box[2:], other_box[2:]) - np.maximum(box[:2], other_box[:2])).prod()
            union = np.maximum(0, box[2:] - box[:2]).prod() + np.maximum(0, other_box[2:] - other_box[:2]).prod() - intersection
            if union > 0 and intersection / union >= .3:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept
