"""Describe image-space tracking output without inventing pitch/event metrics."""
from collections import Counter
import json
import math
from pathlib import Path


def summarize(folder: Path, result: dict) -> dict:
    fps = result["fps"]
    if not isinstance(fps, (float, int)) or not math.isfinite(fps) or fps <= 0 or result["frames"] <= 0 or result["chunks"] <= 0:
        raise ValueError("Thông số kết quả tracking không hợp lệ.")
    tracks, seconds = {}, {}
    groups = Counter({"A": 0, "B": 0, "unknown": 0})
    frames = frames_with_people = observations = maximum = 0
    expected_frame = 0
    for index in range(result["chunks"]):
        payload = json.loads((folder / f"chunk-{index}.json").read_text(encoding="utf-8"))
        for frame in payload["frames"]:
            if frame["frame"] != expected_frame:
                raise ValueError("Kết quả thiếu hoặc trùng frame; không thể tổng hợp báo cáo.")
            expected_frame += 1
            count = len(frame["boxes"])
            frames += 1
            frames_with_people += count > 0
            observations += count
            maximum = max(maximum, count)
            second = int(frame["frame"] / fps)
            bucket = seconds.setdefault(second, {"second": second, "frames": 0, "observations": 0, "maximum": 0, "groups": Counter()})
            bucket["frames"] += 1
            bucket["observations"] += count
            bucket["maximum"] = max(bucket["maximum"], count)
            seen = set()
            for box in frame["boxes"]:
                track_id, group = box["id"], box["group"]
                if track_id in seen or group not in groups:
                    raise ValueError("Kết quả có ID trùng hoặc nhóm màu không hợp lệ.")
                seen.add(track_id)
                groups[group] += 1
                bucket["groups"][group] += 1
                track = tracks.setdefault(track_id, {"id": track_id, "frames": 0, "first_frame": frame["frame"], "last_frame": frame["frame"], "missing_frames": 0, "groups": Counter()})
                if track["frames"]:
                    track["missing_frames"] += frame["frame"] - track["last_frame"] - 1
                track["frames"] += 1
                track["last_frame"] = frame["frame"]
                track["groups"][group] += 1
    if frames != result["frames"] or not frames:
        raise ValueError("Số frame kết quả không khớp video đã xử lý.")
    rows = []
    for track in tracks.values():
        group, support = track["groups"].most_common(1)[0]
        rows.append({"id": track["id"], "group": group if support / track["frames"] >= .7 else "unknown",
                     "frames": track["frames"], "observed_s": track["frames"] / fps,
                     "first_s": track["first_frame"] / fps, "last_s": track["last_frame"] / fps,
                     "missing_s": track["missing_frames"] / fps})
    rows.sort(key=lambda row: (-row["frames"], row["id"]))
    return {"frames": frames, "duration_s": frames / fps, "fps": fps,
            "width": result["width"], "height": result["height"],
            "frames_with_people": frames_with_people, "observations": observations,
            "average_people": observations / frames, "maximum_people": maximum,
            "track_ids": len(tracks), "short_track_ids": sum(row["observed_s"] < 1 for row in rows),
            "unknown_fraction": groups["unknown"] / observations if observations else None,
            "groups": [{"group": group, "observations": groups[group], "average_people": groups[group] / frames} for group in groups],
            "timeline": [{"second": bucket["second"], "average_people": bucket["observations"] / bucket["frames"],
                          "maximum_people": bucket["maximum"], "frames": bucket["frames"]} for bucket in seconds.values()],
            "tracks": rows[:100], "tracks_shown": min(100, len(rows))}
