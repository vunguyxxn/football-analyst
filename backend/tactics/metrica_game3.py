"""Read the pinned Game 3 EPTS variant and compare declared role layouts."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics.formation import analyze_window


def parameters(element):
    result = {}
    for item in element.findall("ProviderParameter"):
        name, value = item.findtext("Name"), item.findtext("Value")
        if name in result:
            raise ValueError("Duplicate metadata parameter")
        result[name] = value
    return result


def read_metadata(path):
    root = ET.parse(path).getroot()
    config = root.find("./Metadata/GlobalConfig")
    fps = float(config.findtext("FrameRate"))
    field = root.find("./Metadata/Sessions/Session/FieldSize")
    if not math.isfinite(fps) or fps <= 0 or (float(field.findtext("Width")), float(field.findtext("Height"))) != (105, 68):
        raise ValueError("Unsupported cadence or pitch")
    score = root.find("./Metadata/Sessions/Session/MatchParameters/Score")
    team_ids = {score.attrib["idLocalTeam"]: "A", score.attrib["idVisitingTeam"]: "B"}
    directions = {}
    for team in root.findall("./Metadata/Teams/Team"):
        value = parameters(team.find("ProviderTeamsParameters"))["attack_direction_first_half"]
        if value not in ("left_to_right", "right_to_left"):
            raise ValueError("Unknown metadata attack direction")
        directions[team_ids[team.attrib["id"]]] = 1 if value == "left_to_right" else -1
    if set(directions) != {"A", "B"} or directions["A"] == directions["B"]:
        raise ValueError("Need opposite attack directions for both teams")
    globals_ = parameters(config.find("ProviderGlobalParameters"))
    periods = {p: (int(globals_[f"{prefix}_start"]), int(globals_[f"{prefix}_end"]))
               for p, prefix in ((1, "first_half"), (2, "second_half"))}
    players, track_ids = {}, set()
    for item in root.findall("./Metadata/Players/Player"):
        pid, team = item.attrib["id"], team_ids[item.attrib["teamId"]]
        shirt = int(item.findtext("ShirtNumber"))
        data = parameters(item.find("ProviderPlayerParameters"))
        xy = [float(data["position_x"]), float(data["position_y"])]
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in xy):
            raise ValueError("Invalid role layout coordinates")
        track_id = shirt + (1000 if team == "B" else 0)
        if pid in players or track_id in track_ids:
            raise ValueError("Duplicate player identity")
        track_ids.add(track_id)
        players[pid] = {"source_player_id": pid, "track_id": track_id, "team": team,
                        "shirt_number": shirt, "role": data["position_type"],
                        "coarse_line_index": int(data["position_index"]),
                        "role_layout_xy_normalized": xy}
    channels = {}
    for item in root.findall("./Metadata/PlayerChannels/PlayerChannel"):
        key = item.attrib["id"]
        if key in channels or item.attrib["playerId"] not in players:
            raise ValueError("Invalid player channel mapping")
        channels[key] = (item.attrib["playerId"], item.attrib["channelId"])
    formats = []
    for item in root.findall("./DataFormatSpecifications/DataFormatSpecification"):
        children = list(item)
        if item.attrib["separator"] != ":" or len(children) != 3 or children[0].tag != "StringRegister" or children[0].attrib["name"] != "frameCount" or children[1].attrib["separator"] != ";":
            raise ValueError("Unsupported EPTS register layout")
        roster = []
        for pair in children[1]:
            refs = [channels[n.attrib["playerChannelId"]] for n in pair]
            if pair.attrib["separator"] != "," or len(refs) != 2 or refs[0][0] != refs[1][0] or [r[1] for r in refs] != ["x", "y"]:
                raise ValueError("Invalid x/y player pair")
            roster.append(refs[0][0])
        start, end = int(item.attrib["startFrame"]), int(item.attrib["endFrame"])
        if start > end or len(set(roster)) != len(roster) or any(sum(players[p]["team"] == t for p in roster) != 11 for t in ("A", "B")):
            raise ValueError("Invalid roster/frame interval")
        formats.append({"start_frame": start, "end_frame": end, "player_ids": roster})
    if not formats or any(b["start_frame"] != a["end_frame"] + 1 for a, b in zip(formats, formats[1:])):
        raise ValueError("Formats must be contiguous and ordered")
    return {"fps": fps, "periods": periods, "directions_first_half": directions,
            "players": players, "formats": formats}


def role_reference(metadata, team, first_frame, last_frame):
    spec = next((s for s in metadata["formats"] if s["start_frame"] <= first_frame <= last_frame <= s["end_frame"]), None)
    if spec is None:
        return {"status": "unknown", "reason": "window_crosses_roster_boundary"}
    players = [metadata["players"][p] for p in spec["player_ids"] if metadata["players"][p]["team"] == team]
    keepers = [p for p in players if p["role"] == "Goalkeeper"]
    if len(keepers) != 1:
        return {"status": "unknown", "reason": "invalid_declared_goalkeeper"}
    outfield = [p for p in players if p not in keepers]
    coarse = Counter(p["coarse_line_index"] for p in outfield)
    depths = Counter(p["role_layout_xy_normalized"][0] for p in outfield)
    return {"status": "declared_role_layout", "goalkeeper_id": keepers[0]["track_id"],
            "role_depth_shape": "-".join(str(depths[x]) for x in sorted(depths)),
            "coarse_shape": "-".join(str(coarse[x]) for x in sorted(coarse)),
            "players": players, "source_format_start_frame": spec["start_frame"],
            "source_format_end_frame": spec["end_frame"], "is_frame_tactical_ground_truth": False}


def load_window(path, metadata, period, start_s, stop_s):
    fps = metadata["fps"]
    period_start, period_end = metadata["periods"][period]
    if not all(math.isfinite(v) for v in (start_s, stop_s)) or start_s < 0 or stop_s <= start_s or stop_s > (period_end - period_start + 1) / fps:
        raise ValueError("Window must lie inside the requested period")
    rows, missing, outside, native, previous = {}, 0, 0, 0, 0
    for p in metadata["players"].values():
        rows[p["track_id"]] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            parts = line.strip().split(":")
            if len(parts) != 3:
                raise ValueError("Unsupported tracking record")
            frame = int(parts[0])
            if frame <= previous:
                raise ValueError("Frames must increase")
            previous = frame
            time_s = (frame - period_start) / fps
            if frame > period_end or time_s >= stop_s:
                break
            if frame < period_start or time_s < start_s:
                continue
            spec = next(s for s in metadata["formats"] if s["start_frame"] <= frame <= s["end_frame"])
            samples = parts[1].split(";")
            if len(samples) != len(spec["player_ids"]):
                raise ValueError("Tracking column count differs from metadata")
            native += 1
            for pid, sample in zip(spec["player_ids"], samples):
                x, y = map(float, sample.split(","))
                if not math.isfinite(x) or not math.isfinite(y):
                    missing += 1
                elif not (0 <= x <= 1 and 0 <= y <= 1):
                    outside += 1
                else:
                    rows[metadata["players"][pid]["track_id"]].append((frame, time_s, x * 105, (1 - y) * 68))
    result = []
    teams = {p["track_id"]: p["team"] for p in metadata["players"].values()}
    for pid, values in rows.items():
        if len(values) < 2:
            continue
        data = np.asarray(values)
        frames = data[:, 0].astype(int)
        result.append(Trajectory(3, pid, teams[pid], frames, data[:, 1], data[:, 2:],
                                 np.r_[0, np.cumsum(np.diff(frames) != 1)], fps))
    if native < 2:
        raise ValueError("Need at least two native frames")
    return result, {"native_frames": native, "missing": missing, "outside": outside}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=60)
    parser.add_argument("--stop", type=int, default=180)
    parser.add_argument("--period", type=int, choices=(1, 2), default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if not output.is_relative_to(root) or output.exists() or args.start < 0 or args.stop <= args.start or (args.stop - args.start) % 10:
        parser.error("Need new output inside project and complete ten-second windows")
    manifest = json.loads((root / "docs/fixtures/metrica_game3_sources.json").read_text(encoding="utf-8"))
    paths = {}
    for item in manifest["files"]:
        path = root / "data/raw/metrica" / item["filename"]
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != item["sha256"]:
            raise ValueError("Game 3 source hash mismatch")
        paths[item["filename"]] = path
    metadata = read_metadata(paths["Sample_Game_3_metadata.xml"])
    tracks, audit = load_window(paths["Sample_Game_3_tracking.txt"], metadata, args.period, args.start, args.stop)
    windows = []
    for team in ("A", "B"):
        direction = metadata["directions_first_half"][team] * (1 if args.period == 1 else -1)
        for start in range(args.start, args.stop, 10):
            first = metadata["periods"][args.period][0] + int(start * metadata["fps"])
            last = first + int(10 * metadata["fps"]) - 1
            reference = role_reference(metadata, team, first, last)
            row = {"team": team, "start_s": start, "stop_s": start + 10, "reference": reference}
            if reference["status"] == "declared_role_layout":
                row["predictions"] = {m: analyze_window([t for t in tracks if t.team == team], start, start + 10,
                                                       reference["goalkeeper_id"], direction, method=m)
                                      for m in ("gap", "template", "aligned")}
            windows.append(row)
    summary = {}
    for method in ("gap", "template", "aligned"):
        counts = Counter()
        for row in windows:
            if "predictions" not in row:
                counts["no_roster_reference"] += 1
                continue
            p = row["predictions"][method]
            counts["abstained" if p["status"] != "observed_shape" else "agrees_with_declared_role_layout" if p["shape"] == row["reference"]["role_depth_shape"] else "differs_from_declared_role_layout"] += 1
        summary[method] = dict(counts)
    report = {"kind": "metrica_game3_role_comparison_v1", "source": manifest, "period": args.period,
              "start_s": args.start, "stop_s": args.stop, "audit": audit, "summary": summary, "windows": windows,
              "reference_kind": "provider_declared_static_role_depths", "is_frame_tactical_ground_truth": False,
              "warning": "Same-game role metadata agreement; not instantaneous tactical formation accuracy"}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
