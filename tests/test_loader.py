import pandas as pd
import pytest
from requests import Response
from requests.exceptions import HTTPError

from backend.tactics import loader
from backend.tactics.loader import MatchNotFoundError, normalize_events


def test_normalize_events_converts_start_and_end_locations() -> None:
    raw_events = pd.DataFrame(
        [
            {
                "minute": 1,
                "second": 2,
                "team": "Home",
                "player": "Player A",
                "player_nickname": "A nickname",
                "type": "Pass",
                "location": [60, 40],
                "end_location": [120, 80],
                "pass_outcome": None,
                "pass_recipient": "Player B",
            },
            {
                "minute": 3,
                "second": 4,
                "team": "Home",
                "player": "Player B",
                "type": "Carry",
                "location": [0, 0],
                "end_location": [60, 40],
            },
            {
                "minute": 5,
                "second": 6,
                "team": "Home",
                "player": "Player A",
                "type": "Shot",
                "location": [120, 80],
                "end_location": [0, 0],
            },
        ]
    )

    events = normalize_events(raw_events, match_id=99)

    assert events["match_id"].tolist() == [99, 99, 99]
    assert events["event_type"].tolist() == ["Pass", "Carry", "Shot"]
    assert events.loc[0, "player_nickname"] == "A nickname"
    assert events.loc[0, ["x_m", "y_m"]].tolist() == pytest.approx([52.5, 34])
    assert events.loc[0, ["end_x_m", "end_y_m"]].tolist() == pytest.approx([105, 0])
    assert events.loc[1, ["x_m", "y_m"]].tolist() == pytest.approx([0, 68])
    assert events.loc[1, ["end_x_m", "end_y_m"]].tolist() == pytest.approx([52.5, 34])
    assert events.loc[2, ["x_m", "y_m"]].tolist() == pytest.approx([105, 0])
    assert events.loc[2, ["end_x_m", "end_y_m"]].tolist() == pytest.approx([0, 68])


def test_load_events_writes_and_reuses_csv_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(loader, "PROCESSED_DATA_DIR", tmp_path)
    monkeypatch.setattr(loader.importlib.util, "find_spec", lambda _: None)
    calls = 0

    def fake_events(match_id: int) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        assert match_id == 99
        return pd.DataFrame(
            [
                {
                    "minute": 1,
                    "second": 2,
                    "team": "Home",
                    "player": "Player A",
                    "type": "Pass",
                    "location": [60, 40],
                    "end_location": [80, 30],
                    "pass_outcome": None,
                    "pass_recipient": "Player B",
                }
            ]
        )

    monkeypatch.setattr(loader.sb, "events", fake_events)
    first_load = loader.load_events(99)
    second_load = loader.load_events(99)

    assert (tmp_path / "events_99.csv").is_file()
    assert calls == 1
    assert second_load.loc[0, "x_m"] == pytest.approx(52.5)
    assert second_load.loc[0, "pass_recipient"] == "Player B"
    assert first_load.loc[0, "end_y_m"] == pytest.approx(42.5)


def test_load_events_maps_upstream_404_to_match_not_found(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(loader, "PROCESSED_DATA_DIR", tmp_path)
    response = Response()
    response.status_code = 404

    def missing_match(match_id: int) -> pd.DataFrame:
        assert match_id == 999
        raise HTTPError(response=response)

    monkeypatch.setattr(loader.sb, "events", missing_match)

    with pytest.raises(MatchNotFoundError, match="Match 999 was not found"):
        loader.load_events(999)
