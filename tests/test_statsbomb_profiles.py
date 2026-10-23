from copy import deepcopy
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

from backend.tactics.statsbomb_profiles import build_profiles, main


@pytest.fixture
def events():
    path = Path(__file__).resolve().parents[1] / "docs/fixtures/statsbomb_8650_tactics.json"
    initial = deepcopy(json.loads(path.read_text(encoding="utf-8"))["events"][:2])
    rows = []
    def add(index, kind, **extra):
        row = dict(id=f"event-{index}", match_id=8650, index=index, period=1,
                   timestamp="00:00:01.000", team="Brazil", event_type=kind,
                   player_id=5547, player="Alisson Ramsés Becker", pass_outcome=None)
        row.update(extra)
        rows.append(row)
    add(3, "Pass")
    add(4, "Pass", pass_outcome="Incomplete")
    add(5, "Carry")
    add(6, "Shot", shot_outcome="Goal")
    add(7, "Player Off", timestamp="00:00:02.000")
    add(8, "Pass", timestamp="00:00:03.000")
    add(9, "Tactical Shift", timestamp="00:00:03.000", player_id=None, player=None,
        tactics=deepcopy(initial[0]["tactics"]))
    add(10, "Pass", timestamp="00:00:03.000")
    add(11, "Substitution", timestamp="00:00:04.000", substitution_replacement_id=9001,
        substitution_replacement="Alex Silva")
    add(12, "Pass", timestamp="00:00:04.500", player_id=9001, player="Alex Silva")
    add(13, "Pass", timestamp="00:00:05.000", player_id=9002, player="Alex Silva")
    add(14, "Own Goal Against", timestamp="00:00:06.000")
    add(15, "Pass", timestamp="00:00:07.000", player_id=None, player="Unidentified player")
    add(16, "Shot", period=5, shot_outcome="Goal")
    return pd.DataFrame(initial + rows)


def test_known_counts_and_zero_event_lineup_players(events):
    report = build_profiles(events, 8650)
    profiles = {p["player_id"]: p for p in report["players"]}
    keeper = profiles[5547]
    assert (keeper["passes_attempted"], keeper["passes_completed"], keeper["pass_completion_pct"]) == (4, 3, 75)
    assert (keeper["carries"], keeper["shots"], keeper["shot_goals"]) == (1, 1, 1)
    assert keeper["recorded_player_events"] == 9
    assert keeper["event_indices"]["Pass"] == [3, 4, 8, 10]
    assert keeper["starter"]
    unused = profiles[5838]
    assert unused["starter"] and unused["recorded_player_events"] == 0
    assert unused["pass_completion_pct"] is None
    assert report["audit"]["excluded_non_playing_period_events"] == 1
    assert report["audit"]["named_events_without_player_id"] == 1
    assert sum(p["recorded_player_events"] for p in report["players"]) == report["audit"]["attributed_player_events"]


def test_role_context_uses_event_index_and_no_future_tactics(events):
    keeper = next(p for p in build_profiles(events, 8650)["players"] if p["player_id"] == 5547)
    contexts = {c["reference_event_index"]: c for c in keeper["role_contexts"]}
    assert contexts[1]["position"]["name"] == "Goalkeeper"
    assert contexts[7]["status"] == "unknown" and contexts[7]["last_event_index"] == 8
    assert contexts[9]["first_event_index"] == contexts[9]["last_event_index"] == 10
    assert contexts[11]["status"] == "unknown"
    assert sum(c["event_count"] for c in contexts.values()) == keeper["recorded_player_events"]


def test_identity_is_not_name_and_replacement_role_not_invented(events):
    profiles = {p["player_id"]: p for p in build_profiles(events, 8650)["players"]}
    one, two = profiles[9001], profiles[9002]
    assert one["player"] == two["player"] == "Alex Silva"
    assert one["short_name"] != two["short_name"]
    assert one["passes_attempted"] == two["passes_attempted"] == 1
    assert not one["starter"] and not two["starter"]
    assert all(c["status"] == "unknown" for c in one["role_contexts"])


def test_missing_outcome_columns_do_not_become_perfect_completion(events):
    report = build_profiles(events.drop(columns=["pass_outcome", "shot_outcome"]), 8650)
    assert report["audit"]["pass_outcome_column_available"] is False
    assert all(p["passes_completed"] is None and p["pass_completion_pct"] is None and p["shot_goals"] is None
               for p in report["players"])


def test_cross_match_cross_team_and_invalid_ids_are_rejected(events):
    with pytest.raises(ValueError, match="requested match"):
        build_profiles(events, 1)
    bad = events.copy()
    bad.loc[bad["index"] == 3, "team"] = "Belgium"
    with pytest.raises(ValueError, match="two teams"):
        build_profiles(bad, 8650)
    bad = events.copy()
    bad.loc[bad["index"] == 3, "player_id"] = 1.5
    with pytest.raises(ValueError, match="positive integer"):
        build_profiles(bad, 8650)
    with pytest.raises(ValueError, match="IDs"):
        build_profiles(events.drop(columns=["player_id"]), 8650)


def test_cli_utf8_source_hash_and_no_overwrite(events, tmp_path, monkeypatch):
    source, output = tmp_path / "events.csv", tmp_path / "profiles.json"
    events.to_csv(source, index=False)
    monkeypatch.setattr(sys, "argv", ["profiles", "--input", str(source), "--match-id", "8650", "--output", str(output)])
    main()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["source_sha256"]) == 64
    assert next(p for p in report["players"] if p["player_id"] == 5547)["player"] == "Alisson Ramsés Becker"
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert output.read_bytes() == before
