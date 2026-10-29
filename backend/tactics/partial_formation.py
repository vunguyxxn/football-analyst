"""Partial geometric formation hypotheses; missing slots are assumptions, never detections."""
import itertools

import numpy as np

from backend.tactics.formation_templates import CATALOG, template_points

POLICY = {"minimum_observed": 6, "maximum_rmse_m": 6., "minimum_margin_m": .75,
          "minimum_temporal_agreement": 2/3, "sample_frames": 3}


def rectangular_assignment(cost):
    """Exact minimum-cost injective assignment (Hungarian), rows <= columns <= 10."""
    cost = np.asarray(cost, dtype=float)
    if cost.ndim != 2 or not 1 <= cost.shape[0] <= cost.shape[1] <= 10 or not np.isfinite(cost).all():
        raise ValueError("Need finite rectangular costs, rows <= columns <=10")
    n,m = cost.shape
    values = cost.tolist()
    u,v,p,way = [0.]*(n+1),[0.]*(m+1),[0]*(m+1),[0]*(m+1)
    for row in range(1,n+1):
        p[0], column = row, 0
        minimum,used = [float("inf")]*(m+1),[False]*(m+1)
        while True:
            used[column] = True
            current,delta,next_column = p[column],float("inf"),0
            for target in range(1,m+1):
                if not used[target]:
                    score = values[current-1][target-1]-u[current]-v[target]
                    if score < minimum[target]:
                        minimum[target],way[target] = score,column
                    if minimum[target] < delta:
                        delta,next_column = minimum[target],target
            for target in range(m+1):
                if used[target]:
                    u[p[target]] += delta
                    v[target] -= delta
                else:
                    minimum[target] -= delta
            column = next_column
            if p[column] == 0:
                break
        while column:
            previous = way[column]
            p[column] = p[previous]
            column = previous
    assignment = [0]*n
    for column in range(1,m+1):
        if p[column]:
            assignment[p[column]-1] = column-1
    return sum(values[row][target] for row,target in enumerate(assignment)),assignment


def fit_snapshot(people):
    if not POLICY["minimum_observed"] <= len(people) <= 10:
        return []
    xy = np.asarray([[row["x_m"],row["y_m"]] for row in people],dtype=float)
    if not np.isfinite(xy).all() or (xy < 0).any() or (xy > [105,68]).any():
        raise ValueError("Positions must be finite pitch coordinates")
    depth,width = np.ptp(xy,axis=0)
    if depth < 12 or width < 12:
        return []
    center = (xy.min(axis=0)+xy.max(axis=0))/2
    depths = sorted({float(max(24,depth)),float(min(75,max(30,depth*1.4)))})
    widths = sorted({float(max(28,width)),float(min(64,max(36,width*1.4)))})
    candidates = []
    for shape in CATALOG:
        relative = template_points(shape)
        best = None
        for length,breadth,dx,dy,direction in itertools.product(depths,widths,(-.25,0,.25),(-.25,0,.25),(-1,1)):
            target = relative * [direction*length/2,breadth/2]+center+[dx*length,dy*breadth]
            if (target < [2,2]).any() or (target > [103,66]).any():
                continue
            cost = np.square(xy[:,None,:]-target[None,:,:]).sum(axis=2)
            total,assignment = rectangular_assignment(cost)
            rmse = float(np.sqrt(total/len(xy)))
            if best is None or rmse < best["rmse_m"]:
                used = set(assignment)
                best = {"shape": shape, "rmse_m": rmse, "attack_direction_hypothesis": direction,
                        "observed_to_slot": [{"id": row["track_id"],"slot": assignment[index]+1} for index,row in enumerate(people)],
                        "unseen_slots": [{"slot": index+1,"x_m": float(point[0]),"y_m": float(point[1]),"status": "hypothetical_not_observed"}
                                         for index,point in enumerate(target) if index not in used]}
        if best:
            # Refine translation/extent using only matched visible slots. A missing
            # whole line must not force the observed bounding box to be the team's.
            assignment = [item["slot"]-1 for item in best["observed_to_slot"]]
            for _ in range(6):
                selected = relative[assignment]
                scales, shifts = [], []
                for axis, limits in ((0, (12., 37.5)), (1, (14., 32.))):
                    direction = best["attack_direction_hypothesis"] if axis == 0 else 1
                    values = selected[:, axis] * direction
                    variance = float(np.var(values))
                    slope = float(np.mean((values-values.mean())*(xy[:,axis]-xy[:,axis].mean()))/variance) if variance > 1e-8 else limits[0]
                    slope = float(np.clip(slope, *limits))
                    scales.append(slope*direction)
                    shifts.append(float(np.mean(xy[:,axis]-values*slope)))
                target = relative * scales + shifts
                if (target < [2,2]).any() or (target > [103,66]).any():
                    break
                total, updated = rectangular_assignment(np.square(xy[:,None,:]-target[None,:,:]).sum(axis=2))
                rmse = float(np.sqrt(total/len(xy)))
                if rmse >= best["rmse_m"]-1e-9:
                    break
                assignment = updated
                best.update(rmse_m=rmse,
                            observed_to_slot=[{"id": row["track_id"], "slot": assignment[index]+1} for index,row in enumerate(people)],
                            unseen_slots=[{"slot": index+1, "x_m": float(point[0]), "y_m": float(point[1]), "status": "hypothetical_not_observed"}
                                          for index,point in enumerate(target) if index not in assignment])
            candidates.append(best)
    return sorted(candidates,key=lambda item:(item["rmse_m"],item["shape"]))


def infer_partial(frames, representative):
    eligible = sorted(frame for frame,people in frames.items() if POLICY["minimum_observed"] <= len(people) <= 10)
    base = {"shape": None, "status": "insufficient_geometry", "confidence": "low",
            "reason": "Cần ít nhất 6 đối tượng cùng nhóm và đủ độ trải để so giả thuyết hình học; không yêu cầu thấy đủ 11 người.",
            "candidates": [], "policy": POLICY,
            "limits": "Nhóm áo/vai trò/hướng tấn công chưa xác nhận. Vị trí khuất là giả định của mẫu, không được đưa vào heatmap, quãng đường hay số người quan sát."}
    if not eligible:
        return base
    selected = sorted({eligible[index] for index in np.linspace(0,len(eligible)-1,POLICY["sample_frames"],dtype=int)})
    if representative in eligible:
        selected = sorted(set(selected+[representative]))
    fits = {frame:fit_snapshot(frames[frame]) for frame in selected}
    fits = {frame:fit for frame,fit in fits.items() if fit}
    if not fits:
        return base
    ranked = []
    for shape in CATALOG:
        samples = [next((item for item in fit if item["shape"] == shape),None) for fit in fits.values()]
        if any(item is None for item in samples):
            continue
        reference_frame = representative if representative in fits else min(fits,key=lambda frame:abs(frame-representative))
        reference = next(item for item in fits[reference_frame] if item["shape"] == shape)
        ranked.append({**reference,"rmse_m": float(np.median([item["rmse_m"] for item in samples])),
                       "agreement": sum(fit[0]["shape"] == shape for fit in fits.values())/len(fits),
                       "reference_frame": reference_frame, "observed_people": len(frames[reference_frame]),
                       "reference_time_s": frames[reference_frame][0]["time_s"],
                       "observed_players": [{"id": row["track_id"], "x_m": row["x_m"], "y_m": row["y_m"]} for row in frames[reference_frame]],
                       "missing_outfield_slots": 10-len(frames[reference_frame])})
    ranked.sort(key=lambda item:(item["rmse_m"],item["shape"]))
    if not ranked:
        return base
    best = ranked[0]
    margin = ranked[1]["rmse_m"]-best["rmse_m"] if len(ranked)>1 else None
    distinct = (margin is not None and margin >= POLICY["minimum_margin_m"] and best["rmse_m"] <= POLICY["maximum_rmse_m"]
                and best["agreement"] >= POLICY["minimum_temporal_agreement"] and len(fits)>=3)
    poor_fit = best["rmse_m"] > POLICY["maximum_rmse_m"]
    return {**base,"status": "poor_template_fit" if poor_fit else "tentative_partial_shape" if distinct else "ambiguous_partial_shapes",
            "shape": best["shape"] if distinct else None,"candidates": ranked[:3],"score_margin_m": margin,
            "sampled_frames": sorted(fits),
            "reason": "Các mẫu thử chưa khớp đủ tốt; không chốt sơ đồ từ đoạn này." if poor_fit else "Ước lượng hình học từ phần đội đang thấy; chưa phải đội hình được xác nhận." if distinct
                      else "Nhiều sơ đồ cùng phù hợp phần đang thấy; giữ các giả thuyết thay vì chốt một sơ đồ."}
