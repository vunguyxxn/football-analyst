"""Offline player event profiles, linked to same-match tactical references."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from backend.tactics.pass_network import _is_missing, _short_names
from backend.tactics.statsbomb_formation import build_timeline


def player_id(value):
    if _is_missing(value):
        return None
    number = float(value)
    if not math.isfinite(number) or number <= 0 or not number.is_integer():
        raise ValueError("Player ID must be a positive integer")
    return int(number)


def build_profiles(events, match_id):
    if not {"player_id", "player"}.issubset(events.columns):
        raise ValueError("Need player IDs and names, not name-only identity matching")
    timeline = build_timeline(events, match_id)
    ordered = events.sort_values("index").to_dict("records")
    profiles, player_teams, nicknames = {}, {}, {}
    context_counts = {}
    attributed, unattributed, excluded = 0, 0, 0
    outcomes_available = "pass_outcome" in events.columns
    goals_available = "shot_outcome" in events.columns

    def register(team, pid, name, *, starter=False, jersey=None):
        if pid is None:
            return None
        if not isinstance(team, str) or not team.strip():
            raise ValueError("Player must belong to a named team")
        if pid in player_teams and player_teams[pid] != team:
            raise ValueError("Same player ID cannot belong to two teams in one match")
        player_teams[pid] = team
        if pid not in profiles:
            profiles[pid] = {"match_id": match_id, "team": team, "player_id": pid,
                             "player": str(name) if not _is_missing(name) else f"Player {pid}",
                             "starter": starter, "jersey_number": jersey,
                             "recorded_player_events": 0, "passes_attempted": 0,
                             "passes_completed": 0 if outcomes_available else None,
                             "carries": 0, "shots": 0, "shot_goals": 0 if goals_available else None,
                             "event_indices": {"Pass": [], "Carry": [], "Shot": []}}
            context_counts[pid] = {}
        else:
            profiles[pid]["starter"] |= starter
            if profiles[pid]["jersey_number"] is None:
                profiles[pid]["jersey_number"] = jersey
        return profiles[pid]

    # Build a same-match identity catalog; keep lineup players with zero events.
    for snapshot in timeline["snapshots"]:
        if snapshot["status"] != "reference":
            continue
        for entry in snapshot["lineup"]:
            register(snapshot["team"], entry["player"]["id"], entry["player"]["name"],
                     starter=snapshot["event_type"] == "Starting XI" and snapshot["period"] == 1,
                     jersey=entry.get("jersey_number"))

    snapshots = {s["event_index"]: s for s in timeline["snapshots"]}
    states = {}
    for row in ordered:
        period, index = int(row["period"]), int(row["index"])
        if period not in (1, 2, 3, 4):
            excluded += 1
            continue  # No penalty-shootout player totals.
        if index in snapshots:
            states[row["team"]] = snapshots[index]
        team = row["team"]
        pid = player_id(row.get("player_id"))
        profile = register(team, pid, row.get("player"))
        if row["event_type"] == "Substitution":
            register(team, player_id(row.get("substitution_replacement_id")), row.get("substitution_replacement"))
        if profile is None:
            if not _is_missing(row.get("player")):
                unattributed += 1
            continue
        nickname = row.get("player_nickname")
        if not _is_missing(nickname) and str(nickname).strip():
            nicknames[pid] = str(nickname).strip()
        attributed += 1
        profile["recorded_player_events"] += 1
        kind = row["event_type"]
        if kind in profile["event_indices"]:
            profile["event_indices"][kind].append(index)
        if kind == "Pass":
            profile["passes_attempted"] += 1
            if outcomes_available and _is_missing(row.get("pass_outcome")):
                profile["passes_completed"] += 1
        elif kind == "Carry":
            profile["carries"] += 1
        elif kind == "Shot":
            profile["shots"] += 1
            if goals_available and row.get("shot_outcome") == "Goal":
                profile["shot_goals"] += 1
        state = states.get(team)
        entry = next((p for p in state.get("lineup", []) if p["player"]["id"] == pid), None) if state else None
        known = state is not None and state["status"] == "reference" and entry is not None
        reason = None if known else state.get("reason", "player_not_in_reference_lineup") if state else "no_prior_reference"
        key = (state["event_index"] if state else None, entry["position"]["id"] if known else None)
        context = context_counts[pid].setdefault(key, {
            "status": "reference" if known else "unknown", "reason": reason,
            "reference_event_index": state["event_index"] if state else None,
            "shape": state["shape"] if known else None,
            "position": entry["position"] if known else None,
            "first_event_index": index, "last_event_index": index, "event_count": 0})
        context["last_event_index"], context["event_count"] = index, context["event_count"] + 1

    for team in sorted(set(player_teams.values())):
        members = [p for p in profiles.values() if p["team"] == team]
        names = sorted({p["player"] for p in members})
        nickname_by_name = {p["player"]: nicknames[p["player_id"]] for p in members if p["player_id"] in nicknames}
        short = _short_names(names, nickname_by_name)
        duplicate = Counter(p["player"] for p in members)
        for profile in members:
            pid, attempted = profile["player_id"], profile["passes_attempted"]
            profile["short_name"] = short[profile["player"]] + (f" (#{pid})" if duplicate[profile["player"]] > 1 else "")
            profile["pass_completion_pct"] = 100 * profile["passes_completed"] / attempted if outcomes_available and attempted else None
            profile["role_contexts"] = list(context_counts[pid].values())
    return {"kind": "statsbomb_player_profiles_v1", "source": "statsbomb", "match_id": match_id,
            "players": sorted(profiles.values(), key=lambda p: (p["team"], p["player_id"])),
            "audit": {"attributed_player_events": attributed, "named_events_without_player_id": unattributed,
                      "excluded_non_playing_period_events": excluded, "pass_outcome_column_available": outcomes_available,
                      "shot_outcome_column_available": goals_available},
            "formation_timeline": timeline,
            "limitations": ["Event counts are not touches, minutes played, distances or off-ball average positions",
                            "Shot goals exclude own goals and penalty shootouts; not final match score",
                            "Role context may be unknown after personnel changes; no inferred replacement role",
                            "No cross-match or Metrica identity mapping; no xG model"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source, output = args.input.resolve(), args.output.resolve()
    if not source.is_relative_to(root) or not output.is_relative_to(root) or output.exists():
        parser.error("Need input inside project and new output inside project")
    result = build_profiles(pd.read_csv(source), args.match_id)
    with source.open("rb") as stream:
        result["source_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    result["source_path"] = source.relative_to(root).as_posix()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"{len(result['players'])} player profiles -> {output}")


if __name__ == "__main__":
    main()
