"""Temporal spatial comparisons of the same simultaneously observed tracking cohort."""
from collections import Counter

import numpy as np

POLICY = {"minimum_common_ids": 4, "stable_frame_share": .7, "minimum_seconds": 5.,
          "minimum_frame_coverage": .5, "maximum_gap_s": .2,
          "extent_change_m": 3., "neighbor_change_m": 2., "forward_change_m": 5.}


def group_frames(by_frame, window):
    return {frame: people for frame, rows in by_frame.items()
            if window["start_s"] <= rows[0]["time_s"] < window["end_s"]
            and 4 <= len(people := [r for r in rows if r["team"] == window["group"]]) <= 11}


def cohort_summary(frames, cohort, window, fps):
    matched = {frame: [row for row in people if row["track_id"] in cohort]
               for frame, people in frames.items() if cohort <= {row["track_id"] for row in people}}
    coverage = len(matched)/max(1, round((window["end_s"]-window["start_s"])*fps))
    support = {"seconds": len(matched)/fps, "frame_coverage": coverage}
    if support["seconds"] < POLICY["minimum_seconds"] or coverage < POLICY["minimum_frame_coverage"]:
        return {"support": support, "metrics": None, "evidence_time_s": None}
    widths, depths, nearest, centers = [], [], [], []
    for people in matched.values():
        xy = np.asarray([[r["x_m"], r["y_m"]] for r in people])
        widths.append(float(np.ptp(xy[:, 1])))
        depths.append(float(np.ptp(xy[:, 0])))
        distance = np.linalg.norm(xy[:, None]-xy[None, :], axis=2)
        np.fill_diagonal(distance, np.inf)
        nearest.append(float(np.median(distance.min(axis=1))))
        centers.append(xy.mean(axis=0))
    representative = min(matched, key=lambda f: abs(f/fps-(window["start_s"]+window["end_s"])/2))
    return {"support": support, "metrics": {"width_m": float(np.median(widths)), "depth_m": float(np.median(depths)),
                                             "nearest_m": float(np.median(nearest)),
                                             "center_x_m": float(np.median(centers, axis=0)[0])},
            "evidence_time_s": representative/fps}


def compare(before, after, by_frame, fps):
    base = {"group": before["group"], "from_segment": before["segment"], "to_segment": after["segment"],
            "from_interval": [before["start_s"], before["end_s"]], "to_interval": [after["start_s"], after["end_s"]],
            "cohort_ids": [], "before": None, "after": None, "deltas": None, "observations": []}
    if before["status"] != "observed_cluster" or after["status"] != "observed_cluster":
        return {**base, "status": "insufficient_windows", "reason": "Một trong hai đoạn chưa đủ dữ liệu; không nối qua đoạn thiếu."}
    if not 0 <= after["start_s"]-before["end_s"] <= POLICY["maximum_gap_s"]:
        return {**base, "status": "gap_between_windows", "reason": "Có khoảng gián đoạn; không suy diễn chuyển trạng thái qua khoảng trống."}
    frames = [group_frames(by_frame, window) for window in (before, after)]
    stable = []
    for items in frames:
        counts = Counter(r["track_id"] for people in items.values() for r in people)
        stable.append({ident for ident, count in counts.items() if count/max(1, len(items)) >= POLICY["stable_frame_share"]})
    cohort = stable[0] & stable[1]
    base["cohort_ids"] = sorted(cohort)
    if len(cohort) < POLICY["minimum_common_ids"]:
        return {**base, "status": "insufficient_common_ids", "reason": "Không đủ cùng ID ổn định ở cả hai đoạn; thay đổi số người thấy không chứng minh đội đổi chiến thuật."}
    a, b = [cohort_summary(items, cohort, window, fps) for items, window in zip(frames, (before, after))]
    base.update(before=a, after=b)
    if a["metrics"] is None or b["metrics"] is None:
        return {**base, "status": "insufficient_joint_visibility", "reason": "Nhóm ID chung chưa cùng hiện đủ 5 giây và 50% ở mỗi đoạn."}
    delta = {key: b["metrics"][key]-a["metrics"][key] for key in a["metrics"]}
    direction_a, direction_b = [(window.get("review") or {}).get("attack_direction") for window in (before, after)]
    same_direction = direction_a in (-1, 1) and direction_a == direction_b
    delta["forward_m"] = delta["center_x_m"]*direction_a if same_direction else None
    observations = []
    for key, threshold, label, positive, negative, check in (
        ("width_m", POLICY["extent_change_m"], "Bề ngang", "rộng hơn", "hẹp hơn", "Nếu đang phòng ngự, rà liên kết ngang; nếu có bóng, kiểm tra người nhận rộng và bọc lót."),
        ("depth_m", POLICY["extent_change_m"], "Chiều dọc", "dài hơn", "ngắn hơn", "Xem hai pha có cùng trạng thái không; kiểm tra các điểm hỗ trợ trước khi kết luận các tuyến giãn hoặc co."),
        ("nearest_m", POLICY["neighbor_change_m"], "Cự ly người cùng nhóm gần nhất", "xa hơn", "gần hơn", "Nếu đang triển khai có bóng, xem khoảng cách hỗ trợ và phương án nhận trung gian; người ngoài nhóm so sánh vẫn có thể hỗ trợ.")):
        value = delta[key]
        if abs(value) >= threshold:
            observations.append({"metric": key, "before": a["metrics"][key], "after": b["metrics"][key], "delta": value,
                                 "text": f"{label} của cụm {len(cohort)} ID {positive if value > 0 else negative} {abs(value):.1f} m.",
                                 "coach_check": check})
    if delta["forward_m"] is not None and abs(delta["forward_m"]) >= POLICY["forward_change_m"]:
        value = delta["forward_m"]
        before_forward = a["metrics"]["center_x_m"] if direction_a == 1 else 105-a["metrics"]["center_x_m"]
        after_forward = b["metrics"]["center_x_m"] if direction_a == 1 else 105-b["metrics"]["center_x_m"]
        observations.append({"metric": "forward_m", "before": before_forward, "after": after_forward,
                             "delta": value, "text": f"Tâm cụm {len(cohort)} ID dịch {abs(value):.1f} m {'về phía tấn công' if value > 0 else 'về phía sân nhà'} theo hướng suy luận.",
                             "coach_check": "Không coi đây là quãng đường hoặc tốc độ; camera, cầu thủ khuất và hiệu chỉnh khác nhau có thể ảnh hưởng. Xem bọc lót và trạng thái bóng ở cả hai đoạn."})
    return {**base, "status": "observed_cohort_comparison", "reason": "So cùng các ID thực sự cùng xuất hiện; chỉ mô tả cụm quan sát, chưa xác nhận thay đổi chiến thuật toàn đội.",
            "deltas": delta, "observations": observations,
            "direction_status": "same_agent_inferred_direction" if same_direction else "unknown_or_changed"}


def build_timeline(windows, by_frame, fps):
    groups = []
    for group in ("A", "B"):
        ordered = sorted((w for w in windows if w["group"] == group), key=lambda w: w["start_s"])
        groups.append({"group": group,
                       "entries": [{"segment": w["segment"], "start_s": w["start_s"], "end_s": w["end_s"], "status": w["status"],
                                    "seconds": w["support"]["seconds"], "evidence_time_s": w["snapshot"]["time_s"] if w["snapshot"] else None} for w in ordered],
                       "comparisons": [compare(a, b, by_frame, fps) for a, b in zip(ordered, ordered[1:])]})
    return {"kind": "observed_cohort_timeline_v1", "policy": POLICY, "groups": groups,
            "limits": "ID có thể đổi/nhầm khi che khuất; nhóm chung không đại diện toàn đội. Không biết pha bóng, không chốt đổi sơ đồ, không suy nguyên nhân/hiệu quả chiến thuật. Tọa độ giữa các mốc vẫn là ước lượng."}
