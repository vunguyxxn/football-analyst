from io import StringIO
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from requests.exceptions import ConnectionError

from backend.app.main import app
from backend.common.metric_catalog import metric_definitions
from backend.tactics import loader
from backend.tactics.event_metrics import compute_event_metrics
from backend.tactics.verify_event_metrics import verify_reference

client = TestClient(app)


def event(team="A", kind="Pass", x=70, **extra):
    return {"team": team, "event_type": kind, "x_m": x, "period": 1,
            "pass_outcome": None, "pass_type": None, "duel_type": None,
            "pass_cross": None, "pass_body_part": None, "shot_statsbomb_xg": None, **extra}


def values(events, team="A"):
    result = compute_event_metrics(events, team)
    return {item.key: item.value for item in result.metrics}


def test_ppda_uses_opposite_team_zones_actions_and_extra_time():
    rows = [event(kind=kind, x=42, **fields) for kind, fields in [
        ("Duel", {"duel_type": "Tackle"}), ("Interception", {}), ("Dribbled Past", {}),
        ("Foul Committed", {}), ("Pass", {"pass_type": "Interception"})]]
    rows += [event(kind="Duel", x=42, duel_type="Aerial Lost"),
             event(kind="Pressure", x=42), event(kind="Ball Recovery", x=42),
             event(kind="Interception", x=41.999), event(kind="Interception", period=4),
             event(kind="Interception", period=5),
             event("B", x=62.999), event("B", x=63), event("B", x=20),
             event("B", x=20, pass_outcome="Incomplete"), event("B", x=20, period=4),
             event("B", x=20, period=5)]
    assert values(pd.DataFrame(rows))["ppda.statsbomb-hudl"] == .5


def test_field_tilt_counts_failed_passes_but_excludes_crosses_throws_and_keeper_arm():
    rows = [event(), event(x=69.999), event(pass_cross=True),
            event(pass_type="Throw-in"), event(pass_body_part="Keeper Arm"),
            event(period=5), event("B", pass_outcome="Incomplete"), event("B", period=4)]
    frame = pd.DataFrame(rows)
    assert values(frame)["field_tilt.stats-perform-2016"] == .3333
    assert values(frame, "B")["field_tilt.stats-perform-2016"] == .6667
    assert values(pd.read_csv(StringIO(frame.to_csv(index=False)))) == values(frame)


def test_completion_and_provider_xg_are_full_match_and_exclude_shootout():
    frame = pd.DataFrame([event(), event(pass_outcome="Out"), event(period=4),
                          event(pass_outcome="Unknown"), event(pass_outcome="Pass Offside"),
                          event(period=5), event(kind="Shot", shot_statsbomb_xg=.2),
                          event(kind="Shot", period=4, shot_statsbomb_xg=.8),
                          event(kind="Shot", period=5, shot_statsbomb_xg=.9), event("B")])
    measured = values(frame)
    assert measured["pass_completion.statsbomb-hudl"] == .4
    assert measured["xg.statsbomb-hudl"] == 1.


@pytest.mark.parametrize("column,key", [("period", "ppda.statsbomb-hudl"),
    ("pass_outcome", "pass_completion.statsbomb-hudl"), ("pass_type", "ppda.statsbomb-hudl"),
    ("duel_type", "ppda.statsbomb-hudl"), ("pass_cross", "field_tilt.stats-perform-2016"),
    ("pass_body_part", "field_tilt.stats-perform-2016"), ("shot_statsbomb_xg", "xg.statsbomb-hudl")])
def test_missing_column_never_implies_success_or_zero(column, key):
    frame = pd.DataFrame([event(), event("B")]).drop(columns=column)
    assert isinstance(values(frame)[key], str)


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1, 106, "invalid"])
def test_missing_or_invalid_position_makes_zone_metrics_unavailable_only(bad):
    frame = pd.DataFrame([event(x=bad), event("B")])
    measured = values(frame)
    assert isinstance(measured["ppda.statsbomb-hudl"], str)
    assert isinstance(measured["field_tilt.stats-perform-2016"], str)
    assert measured["pass_completion.statsbomb-hudl"] == 1


@pytest.mark.parametrize("bad", [None, float("nan"), -1, 1.1, float("inf"), "invalid"])
def test_partial_xg_is_not_a_total(bad):
    frame = pd.DataFrame([event(kind="Shot", shot_statsbomb_xg=.2),
                          event(kind="Shot", shot_statsbomb_xg=bad), event("B")])
    assert isinstance(values(frame)["xg.statsbomb-hudl"], str)


def test_zero_denominators_are_unavailable_and_no_shots_is_valid_zero():
    frame = pd.DataFrame([event(kind="Pressure"), event("B", kind="Pressure")])
    measured = values(frame)
    assert measured["xg.statsbomb-hudl"] == 0
    assert all(isinstance(value, str) for key, value in measured.items() if key != "xg.statsbomb-hudl")


@pytest.mark.parametrize("period", [None, 0, 1.5, 6, float("inf")])
def test_unknown_period_cannot_silently_enter_full_match_totals(period):
    assert all(isinstance(v, str) for v in values(pd.DataFrame([event(period=period), event("B")])).values())


def test_unknown_duel_or_cross_flag_is_not_silently_counted():
    frame = pd.DataFrame([event(kind="Duel", duel_type=None), event("B", pass_cross="maybe")])
    measured = values(frame)
    assert isinstance(measured["ppda.statsbomb-hudl"], str)
    assert isinstance(measured["field_tilt.stats-perform-2016"], str)


def test_loader_normalizes_named_details_before_csv_and_preserves_absent_columns():
    frame = pd.DataFrame([event(kind="Duel", duel_type={"id": 11, "name": "Tackle"}, x=42),
                          event("B", x=20, pass_type={"id": 65, "name": "Interception"}),
                          event("B", pass_body_part={"id": 69, "name": "Keeper Arm"})])
    frame["location"] = [[48, 40], [20 * 120 / 105, 40], [80, 40]]
    normalized = loader.normalize_events(frame, 99)
    assert normalized.loc[0, "duel_type"] == "Tackle"
    assert normalized.loc[1, "pass_type"] == "Interception"
    assert normalized.loc[2, "pass_body_part"] == "Keeper Arm"
    assert values(normalized) == values(pd.read_csv(StringIO(normalized.to_csv(index=False))))
    assert "pass_outcome" not in loader.normalize_events(frame.drop(columns="pass_outcome"), 99)


@pytest.mark.parametrize("outcome", ["not an outcome", {"bad": "mapping"}, 42])
def test_invalid_outcomes_are_unavailable_instead_of_perfect_completion(outcome):
    measured = values(pd.DataFrame([event(pass_outcome=outcome), event("B")]))
    assert isinstance(measured["pass_completion.statsbomb-hudl"], str)
    assert isinstance(measured["ppda.statsbomb-hudl"], str)


def test_mixed_matches_or_one_team_cannot_be_reported_as_full_match_metrics():
    frame = pd.DataFrame([event(match_id=1), event("B", match_id=2)])
    assert all(isinstance(value, str) for value in values(frame).values())
    assert all(isinstance(value, str) for value in values(pd.DataFrame([event()])).values())


def test_catalog_covers_computed_metrics_and_keeps_project_xg_separate():
    cards = {card.key: card for card in metric_definitions()}
    assert cards["field_tilt.stats-perform-2016"].mapping == "approximation"
    assert cards["xg.football-analyst-pre-shot-v1"].implementation == "documented"
    assert all(key in cards for key in values(pd.DataFrame([event(), event("B")])))
    assert cards["video.visible-median-width-v1"].source == "video"


def test_api_preserves_analysis_result_contract_and_uses_catalog(monkeypatch):
    monkeypatch.setattr(loader, "load_events", lambda _: pd.DataFrame([event(), event("B")]))
    response = client.get("/api/matches/99/event-metrics", params={"team": "A"})
    assert response.status_code == 200
    assert set(response.json()) == {"source", "metrics"}
    assert response.json()["source"] == "statsbomb"
    definitions = client.get("/api/matches/metric-definitions")
    assert definitions.status_code == 200
    cards = {card["key"]: card for card in definitions.json()}
    for metric in response.json()["metrics"]:
        assert set(metric) == {"key", "label", "value", "unit", "scope", "subject"}
        assert metric["subject"] == "A" and metric["scope"] == "team"
        assert metric["label"] == cards[metric["key"]]["label"]
    assert client.get("/api/matches/99/event-metrics", params={"team": "Other"}).status_code == 422
    monkeypatch.setattr(loader, "load_events", lambda _: pd.DataFrame([event(match_id=1), event("B", match_id=1)]))
    assert client.get("/api/matches/99/event-metrics", params={"team": "A"}).status_code == 422


def test_api_distinguishes_missing_match_upstream_failure_and_bad_request(monkeypatch):
    for exception, status in [(loader.MatchNotFoundError("missing"), 404), (ConnectionError("offline"), 502)]:
        def fail(_):
            raise exception
        monkeypatch.setattr(loader, "load_events", fail)
        assert client.get("/api/matches/99/event-metrics", params={"team": "A"}).status_code == status
    assert client.get("/api/matches/99/event-metrics", params={"team": ""}).status_code == 422


def test_pinned_world_cup_reference_and_csv_round_trip():
    root = Path(__file__).resolve().parents[1]
    spec = json.loads((root / "docs/fixtures/event_metrics_reference_v1.json").read_text(encoding="utf-8"))
    if not (root / spec["local_events"]).exists():
        pytest.skip("Pinned local StatsBomb source is not present; run offline verifier when available")
    report = verify_reference()
    assert report["csv_round_trip"]
    assert report["results"] == spec["expected"]
