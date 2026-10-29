"""Observed spatial evidence and conditional coaching options; no ball/event dependency."""
from collections import defaultdict
import math

import numpy as np

from backend.tactics.formation_templates import template_points
from backend.tactics.partial_formation import infer_partial
from backend.tactics.video_context import role_for, window_context

POLICY = {"minimum_people": 4, "maximum_people": 11, "minimum_seconds": 5,
          "minimum_frame_coverage": .5, "dominant_lane_share": .6,
          "large_gap_m": 16, "large_gap_frame_share": .3, "narrow_width_m": 32,
          "wide_width_m": 45, "deep_cluster_m": 40, "band_gap_m": 6}
SOURCES = {
    "width": {"title": "FIFA Training Centre · Switch of play", "url": "https://www.fifatrainingcentre.com/en/game/game-analysis/in-possession/switch-of-play.php"},
    "compactness": {"title": "FIFA Training Centre · Team organisation out of possession", "url": "https://www.fifatrainingcentre.com/en/game/game-analysis/out-of-possession/team-organisation--out-of-possession-.php"}}
LANES = ("Dải y thấp (0–22,7 m)", "Trung lộ (22,7–45,3 m)", "Dải y cao (45,3–68 m)")


def formation_option(shape):
    points = template_points(shape)
    return {"shape": shape, "status": "illustration_not_detected_formation", "attack_direction": 1,
            "players": [{"slot": 1, "x_m": 8., "y_m": 34., "role": "goalkeeper"}] +
                       [{"slot": index + 2, "x_m": float(53 + point[0] * 27), "y_m": float(34 + point[1] * 24), "role": "outfield"}
                        for index, point in enumerate(points)]}


def coaching_options(metrics):
    """Engineering thresholds select review topics, never validated optimal tactics."""
    options = []
    shares = metrics["lane_shares"]
    dominant = max(range(3), key=lambda index: shares[index])

    def add(key, title, observation, evidence, phase, actions, risk, shape, source):
        options.append({"id": key, "title": title, "observation": observation, "evidence": evidence,
                        "condition": phase, "actions": actions, "tradeoff": risk,
                        "formation_option": shape, "source": SOURCES[source],
                        "status": "conditional_coaching_option"})

    if shares[dominant] >= POLICY["dominant_lane_share"] or metrics["median_width_m"] < POLICY["narrow_width_m"]:
        add("width", "Tạo chiều rộng và cân nhắc đổi hướng triển khai",
            f"{shares[dominant]*100:.1f}% lượt vị trí trong {LANES[dominant].lower()}; bề ngang cụm trung vị {metrics['median_width_m']:.1f} m.",
            [{"metric": "lane_shares", "index": dominant, "value": shares[dominant]},
             {"metric": "median_width_m", "value": metrics["median_width_m"]}],
            "Chỉ áp dụng khi đội đang có bóng và HLV xác nhận bên đối diện có người nhận/khoảng trống; camera chưa chứng minh phần ngoài khung hình.",
            ["Giữ một phương án nhận rộng ở biên đối diện và một điểm hỗ trợ trung tâm.",
             "Tập luân chuyển qua cầu thủ hỗ trợ trước khi đổi hướng, thay vì ép bóng qua cụm đông người."],
            "Giãn quá sớm có thể làm mất liên kết; cần người bọc lót trước khi hậu vệ biên dâng.", "4-3-3", "width")
    if metrics["large_gap_frame_share"] >= POLICY["large_gap_frame_share"]:
        add("connection", "Tăng điểm hỗ trợ giữa các cụm",
            f"{metrics['large_gap_frame_share']*100:.1f}% thời điểm đủ người có khoảng cách dọc x liền kề từ 16 m; khoảng cách lớn nhất trung vị {metrics['median_largest_x_gap_m']:.1f} m.",
            [{"metric": "large_gap_frame_share", "value": metrics["large_gap_frame_share"]},
             {"metric": "median_largest_x_gap_m", "value": metrics["median_largest_x_gap_m"]}],
            "Nếu đây là pha triển khai có bóng và khoảng cách cũng hiện rõ khi xem video; không coi khoảng trống do người ngoài camera là khoảng cách giữa các tuyến thật.",
            ["Bố trí một người nhận giữa hai cụm và một người hỗ trợ phía sau để tạo tam giác.",
             "Có thể thử vai trò hai tiền vệ hỗ trợ trong 4-2-3-1 rồi so lại cự ly ở các đoạn tương đương."],
            "Kéo quá nhiều người về hỗ trợ có thể làm giảm chiều sâu phía trước.", "4-2-3-1", "width")
    if metrics["median_width_m"] > POLICY["wide_width_m"] or metrics["median_depth_m"] > POLICY["deep_cluster_m"]:
        add("compactness", "Rà cự ly khối phòng ngự",
            f"Cụm quan sát trải ngang {metrics['median_width_m']:.1f} m, dọc {metrics['median_depth_m']:.1f} m (trung vị theo frame).",
            [{"metric": "median_width_m", "value": metrics["median_width_m"]},
             {"metric": "median_depth_m", "value": metrics["median_depth_m"]}],
            "Chỉ áp dụng nếu HLV xác nhận đang phòng ngự ổn định; đội giãn rộng khi có bóng không tự là lỗi.",
            ["Di chuyển các tuyến cùng nhau, bảo vệ trung lộ trước khi một người lao ra áp sát.",
             "Có thể thử khối 4-4-2 trong bài tập phòng ngự và kiểm tra lại khoảng cách hỗ trợ."],
            "Co quá hẹp có thể nhường biên; cần người bọc lót khi đối thủ đổi hướng.", "4-4-2", "compactness")
    if not options:
        add("maintain", "Giữ liên kết và đối chiếu thêm pha tương tự",
            f"Cự ly người gần nhất trung vị {metrics['median_nearest_neighbor_m']:.1f} m; chưa chạm ngưỡng rà hẹp/rộng hoặc đứt cụm của bộ quy tắc.",
            [{"metric": "median_nearest_neighbor_m", "value": metrics["median_nearest_neighbor_m"]}],
            "Đây chỉ là đoạn quan sát ngắn; cần so các pha cùng trạng thái có bóng/không bóng trước khi đổi sơ đồ.",
            ["Giữ các phương án hỗ trợ gần và xem thêm vị trí cầu thủ ngoài khung hình.",
             "Đánh giá vai trò hiện tại trước khi thử thay đổi số tuyến hoặc số người ở mỗi tuyến."],
            "Một đoạn chưa chạm ngưỡng không chứng minh hệ thống chiến thuật đang tối ưu.", "4-2-3-1", "compactness")
    return options


def analyze_window(frame_rows, group, segment, fps, review=None):
    start, end = segment["start_s"], segment["end_s"]
    frames = {frame: [row for row in rows if row["team"] == group]
              for frame, rows in frame_rows.items() if start <= rows[0]["time_s"] < end}
    valid = {frame: rows for frame, rows in frames.items() if POLICY["minimum_people"] <= len(rows) <= POLICY["maximum_people"]}
    expected = max(1, round((end-start)*fps))
    coverage, seconds = len(valid) / expected, len(valid) / fps
    base = {"segment": segment["segment"], "group": group, "start_s": start, "end_s": end,
            "review": review,
            "support": {"frames": len(valid), "seconds": seconds, "frame_coverage": coverage,
                        "minimum_people": POLICY["minimum_people"]},
            "formation": {"status": "insufficient_geometry", "shape": None, "candidates": [],
                          "reason": "Chưa đủ phần vị trí quan sát để ước lượng sơ đồ."}}
    if seconds < POLICY["minimum_seconds"] or coverage < POLICY["minimum_frame_coverage"]:
        return {**base, "status": "insufficient_data", "metrics": None, "heatmap_seconds": None,
                "snapshot": None, "recommendations": []}
    heatmap, lane_counts = np.zeros((14,21)), np.zeros(3)
    widths, depths, nearest, gaps, centers, counts = [], [], [], [], [], []
    for rows in valid.values():
        xy = np.asarray([[row["x_m"], row["y_m"]] for row in rows])
        widths.append(float(np.ptp(xy[:,1])))
        depths.append(float(np.ptp(xy[:,0])))
        centers.append(xy.mean(axis=0))
        counts.append(len(xy))
        distances = np.linalg.norm(xy[:,None,:]-xy[None,:,:], axis=2)
        np.fill_diagonal(distances, np.inf)
        nearest.append(float(np.median(distances.min(axis=1))))
        gaps.append(float(np.max(np.diff(np.sort(xy[:,0])))))
        for x,y in xy:
            heatmap[min(13,int(y/68*14)),min(20,int(x/105*21))] += 1/fps
            lane_counts[min(2,int(y/68*3))] += 1
    metrics = {"median_width_m": float(np.median(widths)), "median_depth_m": float(np.median(depths)),
               "median_nearest_neighbor_m": float(np.median(nearest)), "median_largest_x_gap_m": float(np.median(gaps)),
               "large_gap_frame_share": float(np.mean(np.asarray(gaps) >= POLICY["large_gap_m"])),
               "centroid_m": np.median(centers, axis=0).tolist(), "median_people": float(np.median(counts)),
               "lane_shares": (lane_counts/lane_counts.sum()).tolist(), "observations": int(lane_counts.sum())}
    representative = min(valid, key=lambda frame: (abs(len(valid[frame])-metrics["median_people"]), abs(frame/fps-(start+end)/2)))
    people = sorted(valid[representative], key=lambda row: row["x_m"])
    bands = [[]]
    for person in people:
        if bands[-1] and person["x_m"]-bands[-1][-1]["x_m"] > POLICY["band_gap_m"]:
            bands.append([])
        bands[-1].append(person)
    snapshot = {"frame": representative, "time_s": representative/fps,
                "players": [{"id": row["track_id"], "x_m": row["x_m"], "y_m": row["y_m"]} for row in people],
                "bands": [{"ids": [row["track_id"] for row in band],
                           "centroid_m": np.mean([[row["x_m"],row["y_m"]] for row in band],axis=0).tolist()} for band in bands]}
    return {**base, "formation": infer_partial(valid,representative,review["attack_direction"] if review else None), "status": "observed_cluster", "metrics": metrics, "heatmap_seconds": heatmap.tolist(),
            "snapshot": snapshot, "recommendations": coaching_options(metrics)}


def build_report(rows, calibration, fps, total_frames, context=None):
    if not math.isfinite(fps) or fps <= 0 or total_frames <= 0:
        raise ValueError("Invalid clip timing")
    by_frame, keys = defaultdict(list), set()
    for row in rows:
        frame, track = row["frame"], row["track_id"]
        if (type(frame) is not int or type(track) is not int or not 0 <= frame < total_frames or track < 0
                or not all(type(row[key]) in (int,float) and math.isfinite(row[key]) for key in ("time_s","x_m","y_m"))
                or abs(row["time_s"]-frame/fps) > 1e-5 or not 0 <= row["x_m"] <= 105 or not 0 <= row["y_m"] <= 68
                or row["team"] not in ("A","B","unknown","referee") or (frame,track) in keys):
            raise ValueError("Invalid, duplicate or mismatched pitch row")
        keys.add((frame,track))
        if context is None or role_for(row, context) is None:
            by_frame[frame].append(row)
    segments, previous, ids = calibration["segments"], 0., set()
    for segment in segments:
        start,end = segment["start_s"],segment["end_s"]
        if (not all(type(value) in (int,float) and math.isfinite(value) for value in (start,end))
                or not previous <= start < end <= total_frames/fps or segment["segment"] in ids):
            raise ValueError("Invalid calibration windows")
        previous = end
        ids.add(segment["segment"])
    if any(not any(segment["start_s"] <= row["time_s"] < segment["end_s"] for segment in segments) for row in rows):
        raise ValueError("Pitch rows outside calibrated windows")
    return {"kind": "video_spatial_tactics_v1", "status": "provisional_spatial_analysis",
            "independently_validated": False, "method": "traceable_spatial_rules_not_trained_tactic_model",
            "source_sha256": calibration["source_sha256"], "person_job_id": calibration["person_job_id"],
            "coordinate_system": "105x68_bottom_left", "policy": POLICY,
            "context_review": {"status": "agent_review_not_independent", "audit": context["audit"],
                               "team_labels": context["team_labels"],
                               "removed_team_observations": sum(row["team"] in ("A","B") and role_for(row,context) is not None for row in rows)} if context else None,
            "windows": [analyze_window(by_frame,group,segment,fps,window_context(context,segment,group) if context else None) for segment in segments for group in ("A","B")],
            "formation_options": [formation_option(shape) for shape in ("4-3-3","4-4-2","4-2-3-1")],
            "limits": ["Chỉ mô tả nhóm áo được nhìn thấy trong đoạn có tọa độ; phần ngoài camera không được coi là trống.",
                       "Heatmap là thời gian vị trí quan sát, không phải kiểm soát bóng; chưa biết pha có bóng/không bóng.",
                       "Tọa độ vẫn là hiệu chỉnh tay ước lượng. Gợi ý theo quy tắc là phương án có điều kiện, chưa chứng minh hiệu quả bằng ML/SHAP."]}
