from copy import deepcopy
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

from backend.tactics.statsbomb_formation import (
    build_timeline, compare_window, decode_tactics, main, reference_at, timestamp_seconds,
)


@pytest.fixture
def source():
    return json.loads((Path(__file__).resolve().parents[1] /
                       "docs/fixtures/statsbomb_8650_tactics.json").read_text(encoding="utf-8"))


@pytest.fixture
def timeline(source):
    return build_timeline(pd.DataFrame(source["events"]), 8650)


def test_real_starting_lineups_and_late_formation_change(timeline):
    initial = reference_at(timeline, "Belgium", 1, 0)
    assert initial["shape"] == "4-3-3"
    assert len(initial["lineup"]) == 11
    assert reference_at(timeline, "Belgium", 2, 2227)["shape"] == "4-3-3"
    assert reference_at(timeline, "Belgium", 2, 2227.36)["status"] == "unknown"
    changed = reference_at(timeline, "Belgium", 2, 2234.28)
    assert changed["shape"] == "5-3-2"
    assert 6332 in {p["player"]["id"] for p in changed["lineup"]}
    assert 4831 not in {p["player"]["id"] for p in changed["lineup"]}
    # Later substitution then Tactical Shift: no stale previous lineup.
    assert reference_at(timeline, "Belgium", 2, 2492)["status"] == "unknown"
    last = reference_at(timeline, "Belgium", 2, 2493.067)
    assert 2954 in {p["player"]["id"] for p in last["lineup"]}
    assert reference_at(timeline, "Brazil", 2, 0)["status"] == "unknown"
    assert reference_at(timeline, "Brazil", 2, 1.88)["shape"] == "4-3-3"


def test_temporary_player_off_on_remains_conservative(timeline):
    assert reference_at(timeline, "Brazil", 1, 1612)["status"] == "reference"
    assert reference_at(timeline, "Brazil", 1, 1613)["status"] == "unknown"
    assert reference_at(timeline, "Brazil", 1, 1700)["status"] == "unknown"
    assert reference_at(timeline, "Absent", 1, 0)["reason"] == "no_prior_reference"


def test_window_boundaries_unknown_disagreement_and_cross_match(timeline):
    assert compare_window(timeline, 8650, "Belgium", 1, 0, 10, "4-3-3")["agrees"]
    assert not compare_window(timeline, 8650, "Belgium", 1, 0, 10, "4-4-2")["agrees"]
    assert compare_window(timeline, 8650, "Belgium", 1, 0, 10, None)["reason"] == "observation_unknown"
    assert compare_window(timeline, 8650, "Belgium", 2, 2220, 2240, "5-3-2")["reason"] == "reference_changes_in_window"
    assert compare_window(timeline, 8650, "Belgium", 2, 2220, 2227.36, "4-3-3")["agrees"]
    assert compare_window(timeline, 8650, "Belgium", 2, 2227.36, 2230, "4-3-3")["status"] == "not_comparable"
    with pytest.raises(ValueError, match="same match"):
        compare_window(timeline, 1, "Belgium", 1, 0, 10, "4-3-3")
    with pytest.raises(ValueError):
        compare_window(timeline, 8650, "Belgium", 1, 0, 10, "4-4-3")


def test_event_index_sort_same_timestamp_and_mutation_isolation(source):
    rows = deepcopy(source["events"][:2])
    shift = deepcopy(rows[0])
    shift.update(index=3, event_type="Tactical Shift")
    shift["tactics"]["formation"] = 442
    rows.append(shift)
    result = build_timeline(pd.DataFrame(rows[::-1]), 8650)
    first = reference_at(result, "Brazil", 1, 0)
    assert first["shape"] == "4-4-2"
    first["lineup"].clear()
    assert len(reference_at(result, "Brazil", 1, 0)["lineup"]) == 11


@pytest.mark.parametrize("card", ["Red Card", "Second Yellow"])
def test_dismissal_invalidates_reference(source, card):
    rows = deepcopy(source["events"][:2])
    rows.append(dict(match_id=8650, index=3, period=1, timestamp="00:01:00.000",
                     team="Brazil", event_type="Foul Committed", foul_committed_card=card))
    assert reference_at(build_timeline(pd.DataFrame(rows), 8650), "Brazil", 1, 60)["status"] == "unknown"


def test_invalid_tactics_and_csv_dict_representation(source):
    tactics = source["events"][0]["tactics"]
    assert decode_tactics(repr(tactics))[0] == decode_tactics(json.dumps(tactics))[0] == "4-3-3"
    bad = deepcopy(tactics)
    bad["lineup"][1]["player"] = bad["lineup"][0]["player"]
    with pytest.raises(ValueError):
        decode_tactics(bad)
    rows = deepcopy(source["events"][:2])
    rows[0]["tactics"] = "malformed"
    assert reference_at(build_timeline(pd.DataFrame(rows), 8650), "Brazil", 1, 0)["status"] == "unknown"
    with pytest.raises(ValueError):
        build_timeline(pd.DataFrame(rows), 1)
    with pytest.raises(ValueError):
        build_timeline(pd.DataFrame(rows + [rows[0]]), 8650)


@pytest.mark.parametrize("value", ["nan", "00:61:00", "00:00:nan", "-1:00:00"])
def test_invalid_timestamp(value):
    with pytest.raises(ValueError):
        timestamp_seconds(value)


def test_cli_cache_only_and_no_overwrite(source, tmp_path, monkeypatch):
    csv, output = tmp_path / "events.csv", tmp_path / "reference.json"
    pd.DataFrame(source["events"]).to_csv(csv, index=False)
    monkeypatch.setattr(sys, "argv", ["reference", "--input", str(csv), "--output", str(output),
                                    "--match-id", "8650"])
    main()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert len(result["snapshots"]) == len(source["events"])
    assert len(result["source_sha256"]) == 64
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert output.read_bytes() == before
