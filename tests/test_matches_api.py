import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tactics import loader
from backend.tactics.loader import MatchNotFoundError

client = TestClient(app)


def test_competitions_endpoint_uses_response_model(monkeypatch) -> None:
    monkeypatch.setattr(
        loader,
        "list_competitions",
        lambda: pd.DataFrame(
            [
                {
                    "competition_id": 43,
                    "season_id": 3,
                    "competition_name": "FIFA World Cup",
                    "season_name": "2018",
                    "country_name": "International",
                }
            ]
        ),
    )

    response = client.get("/api/matches/competitions")

    assert response.status_code == 200
    assert response.json()[0]["competition_id"] == 43
    assert response.json()[0]["season_name"] == "2018"


def test_matches_endpoint_uses_response_model(monkeypatch) -> None:
    def fake_list_matches(competition_id: int, season_id: int) -> pd.DataFrame:
        assert (competition_id, season_id) == (43, 3)
        return pd.DataFrame(
            [
                {
                    "match_id": 99,
                    "match_date": "2018-07-15",
                    "home_team": "Home",
                    "away_team": "Away",
                    "home_score": 2,
                    "away_score": 1,
                }
            ]
        )

    monkeypatch.setattr(loader, "list_matches", fake_list_matches)

    response = client.get(
        "/api/matches",
        params={"competition_id": 43, "season_id": 3},
    )

    assert response.status_code == 200
    assert response.json()[0]["match_id"] == 99
    assert response.json()[0]["home_team"] == "Home"


def test_missing_match_returns_clear_404(monkeypatch) -> None:
    def missing_match(match_id: int) -> pd.DataFrame:
        raise MatchNotFoundError(f"Match {match_id} was not found")

    monkeypatch.setattr(loader, "load_events", missing_match)

    response = client.get("/api/matches/999/pass-network", params={"team": "Home"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Match 999 was not found"
