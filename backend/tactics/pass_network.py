from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    missing = pd.isna(value)
    return bool(missing) if not hasattr(missing, "__len__") else False


def _short_names(
    players: list[str],
    nicknames: dict[str, str | None],
) -> dict[str, str]:
    base_names = {
        player: (nicknames.get(player) or player.split()[-1]).strip()
        for player in players
    }
    short_names = base_names.copy()

    for base_name in set(base_names.values()):
        matching_players = [
            player for player, candidate in base_names.items()
            if candidate == base_name
        ]
        if len(matching_players) < 2:
            continue
        for player in matching_players:
            name_parts = player.split()
            initials = [f"{part[0]}." for part in name_parts[:-1] if part]
            if initials:
                short_names[player] = f"{initials[0]} {base_name}"

    while len(set(short_names.values())) != len(short_names):
        duplicate_names = {
            candidate
            for candidate in short_names.values()
            if list(short_names.values()).count(candidate) > 1
        }
        for player, candidate in short_names.items():
            if candidate not in duplicate_names:
                continue
            name_parts = player.split()
            initials = [f"{part[0]}." for part in name_parts[:-1] if part]
            current_initial_count = candidate.split(" ", 1)[0].count(".")
            if current_initial_count < len(initials):
                short_names[player] = (
                    f"{' '.join(initials[:current_initial_count + 1])} "
                    f"{base_names[player]}"
                )
            else:
                short_names[player] = player

        if len(set(short_names.values())) != len(short_names):
            for player, candidate in list(short_names.items()):
                if list(short_names.values()).count(candidate) > 1:
                    short_names[player] = f"{player} ({players.index(player) + 1})"

    return short_names


def compute_pass_network(
    events_df: pd.DataFrame,
    team: str,
    minute_range: tuple[int, int] | None = None,
    min_edge_count: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Build a successful-pass network for one team.

    Only passes with an empty/NaN ``pass_outcome`` count as successful. When no
    minute range is provided, player positions and touches are limited to events
    before the team's first substitution. A supplied inclusive minute range
    replaces that substitution cutoff. Nodes average each player's normalized
    event start locations; edges with fewer than ``min_edge_count`` passes are
    omitted.
    """
    if min_edge_count < 1:
        raise ValueError("min_edge_count must be at least 1")
    if minute_range is not None and minute_range[0] > minute_range[1]:
        raise ValueError("minute_range start must be less than or equal to end")

    events = events_df.copy().reset_index(drop=True)
    required = {"team", "player", "event_type"}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"events_df is missing required columns: {sorted(missing)}")

    team_events = events.loc[events["team"] == team].copy()
    if minute_range is not None:
        if "minute" not in team_events.columns:
            raise ValueError("minute_range requires a minute column")
        team_events = team_events.loc[
            team_events["minute"].between(minute_range[0], minute_range[1], inclusive="both")
        ]
    elif "event_type" in team_events.columns:
        substitutions = team_events.index[
            team_events["event_type"].eq("Substitution")
        ]
        if len(substitutions):
            team_events = team_events.loc[team_events.index < substitutions[0]]

    locations_available = {"x_m", "y_m"}.issubset(team_events.columns)
    located_events = (
        team_events.dropna(subset=["x_m", "y_m"])
        if locations_available
        else team_events.iloc[0:0]
    )
    grouped = located_events.groupby("player", dropna=True)
    positions = grouped[["x_m", "y_m"]].mean()
    touches = team_events.loc[team_events["player"].notna()].groupby("player").size()
    nicknames: dict[str, str | None] = {}
    if "player_nickname" in team_events.columns:
        for player, values in team_events.groupby("player", dropna=True)[
            "player_nickname"
        ]:
            nickname = next(
                (
                    str(value).strip()
                    for value in values
                    if not _is_missing(value) and str(value).strip()
                ),
                None,
            )
            nicknames[str(player)] = nickname

    successful_passes = team_events.loc[
        team_events["event_type"].eq("Pass")
    ].copy()
    if "pass_outcome" in successful_passes.columns:
        successful_passes = successful_passes.loc[
            successful_passes["pass_outcome"].map(_is_missing)
        ]
    else:
        successful_passes = successful_passes.iloc[0:0]

    pass_counts = successful_passes.loc[
        successful_passes["player"].notna()
    ].groupby("player").size()
    player_names = set(positions.index)
    short_names = _short_names(
        [str(player) for player in positions.index],
        nicknames,
    )
    nodes = [
        {
            "player": player,
            "short_name": short_names[str(player)],
            "avg_x_m": float(positions.loc[player, "x_m"]),
            "avg_y_m": float(positions.loc[player, "y_m"]),
            "pass_count": int(pass_counts.get(player, 0)),
            "touches": int(touches.get(player, 0)),
        }
        for player in positions.index
    ]

    edges_counter: Counter[tuple[str, str]] = Counter()
    if "pass_recipient" in successful_passes.columns:
        for _, row in successful_passes.iterrows():
            source = row["player"]
            target = row["pass_recipient"]
            if (
                not _is_missing(source)
                and not _is_missing(target)
                and source in player_names
                and target in player_names
            ):
                edges_counter[(source, target)] += 1

    edges = [
        {"source": source, "target": target, "count": count}
        for (source, target), count in sorted(edges_counter.items())
        if count >= min_edge_count
    ]
    return {"nodes": nodes, "edges": edges}
