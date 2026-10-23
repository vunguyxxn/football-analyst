"""Offline, event-ordered StatsBomb formation references from cached CSV."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


def timestamp_seconds(value):
    parts = str(value).split(":")
    if len(parts) != 3:
        raise ValueError("Expected period-relative HH:MM:SS timestamp")
    hours, minutes, seconds = map(float, parts)
    if not all(math.isfinite(v) for v in (hours, minutes, seconds)) or hours < 0 or not hours.is_integer() or not minutes.is_integer() or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError("Invalid timestamp")
    return hours * 3600 + minutes * 60 + seconds


def decode_tactics(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = ast.literal_eval(value)  # Existing pandas CSV uses Python dict repr.
    if not isinstance(value, dict):
        raise ValueError("Missing tactics object")
    code = str(value.get("formation", ""))
    if not code.isdigit() or "0" in code or sum(map(int, code)) != 10:
        raise ValueError("Unsupported eleven-player formation code")
    lineup = value.get("lineup")
    if not isinstance(lineup, list) or len(lineup) != 11:
        raise ValueError("Need eleven players in reference lineup")
    ids, goalkeepers = [], 0
    for entry in lineup:
        player, position = entry["player"], entry["position"]
        if not isinstance(player["id"], int) or not isinstance(position["id"], int):
            raise ValueError("Invalid player/position ID")
        ids.append(player["id"])
        goalkeepers += position["id"] == 1
    if len(set(ids)) != 11 or goalkeepers != 1:
        raise ValueError("Duplicate player or invalid goalkeeper count")
    return "-".join(code), deepcopy(lineup)


def build_timeline(events, match_id):
    required = {"match_id", "index", "period", "timestamp", "team", "event_type"}
    if not required.issubset(events.columns) or set(events.match_id) != {match_id}:
        raise ValueError("Need events from exactly the requested match")
    if events["index"].duplicated().any():
        raise ValueError("Duplicate event index")
    snapshots = []
    for row in events.sort_values("index").to_dict("records"):
        kind = row["event_type"]
        is_red = any(row.get(key) in ("Red Card", "Second Yellow")
                     for key in ("foul_committed_card", "bad_behaviour_card"))
        if kind not in ("Starting XI", "Tactical Shift", "Substitution", "Player Off", "Player On") and not is_red:
            continue
        snapshot = {"team": row["team"], "period": int(row["period"]),
                    "time_s": timestamp_seconds(row["timestamp"]), "event_index": int(row["index"]),
                    "event_id": row.get("id"), "event_type": kind}
        if snapshot["period"] not in (1, 2, 3, 4):
            continue  # Penalty shootout is not an outfield formation period.
        if kind in ("Starting XI", "Tactical Shift"):
            try:
                shape, lineup = decode_tactics(row.get("tactics"))
                snapshot.update(status="reference", shape=shape, lineup=lineup)
            except (ValueError, TypeError, KeyError, SyntaxError):
                snapshot.update(status="unknown", reason="unsupported_or_invalid_tactics")
        else:
            # Do not invent a new player's role or restore roles after Player On.
            snapshot.update(status="unknown", reason="personnel_change_requires_tactics")
        snapshots.append(snapshot)
    for team in {s["team"] for s in snapshots}:
        keys = [(s["period"], s["time_s"], s["event_index"]) for s in snapshots if s["team"] == team]
        if keys != sorted(keys):
            raise ValueError("Event index conflicts with period/timestamp order")
    return {"kind": "statsbomb_formation_reference_v1", "match_id": match_id, "snapshots": snapshots}


def reference_at(timeline, team, period, time_s):
    if period not in (1, 2, 3, 4) or not math.isfinite(time_s) or time_s < 0:
        raise ValueError("Invalid period/time")
    eligible = [s for s in timeline["snapshots"] if s["team"] == team and
                (s["period"], s["time_s"]) <= (period, time_s)]
    if not eligible:
        return {"status": "unknown", "reason": "no_prior_reference"}
    return deepcopy(eligible[-1])


def compare_window(timeline, match_id, team, period, start_s, stop_s, observed_shape):
    """Compare same-match shape labels; never match cross-source player identities."""
    if match_id != timeline["match_id"]:
        raise ValueError("Reference and observation must have the same match ID")
    if not math.isfinite(stop_s) or stop_s <= start_s:
        raise ValueError("Invalid window")
    ref = reference_at(timeline, team, period, start_s)
    if any(s["team"] == team and s["period"] == period and start_s < s["time_s"] < stop_s
           for s in timeline["snapshots"]):
        return {"status": "not_comparable", "reason": "reference_changes_in_window"}
    if ref["status"] != "reference":
        return {"status": "not_comparable", "reason": ref["reason"]}
    if observed_shape is None:
        return {"status": "not_comparable", "reason": "observation_unknown"}
    parts = str(observed_shape).split("-")
    if not all(p.isdigit() and len(p) == 1 and p != "0" for p in parts) or sum(map(int, parts)) != 10:
        raise ValueError("Invalid observed shape")
    return {"status": "compared", "reference_shape": ref["shape"],
            "observed_shape": observed_shape, "agrees": observed_shape == ref["shape"],
            "reference_event_index": ref["event_index"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source, output = args.input.resolve(), args.output.resolve()
    if not source.is_relative_to(root) or not output.is_relative_to(root):
        parser.error("Paths must stay inside project")
    if output.exists():
        parser.error("Output already exists")
    result = build_timeline(pd.read_csv(source), args.match_id)
    with source.open("rb") as stream:
        result["source_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    result["source_path"] = source.relative_to(root).as_posix()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"{len(result['snapshots'])} snapshots -> {output}")


if __name__ == "__main__":
    main()
