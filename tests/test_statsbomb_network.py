import pytest

from backend.tactics.loader import list_matches, load_events
from backend.tactics.pass_network import compute_pass_network


@pytest.mark.network
def test_world_cup_2018_open_data_has_normalized_event_coordinates() -> None:
    matches = list_matches(competition_id=43, season_id=3)
    assert not matches.empty
    match_id = int(matches.iloc[0]["match_id"])
    events = load_events(match_id)
    assert not events.empty
    assert events["x_m"].dropna().between(0, 105).all()
    assert events["y_m"].dropna().between(0, 68).all()
    team = str(events["team"].dropna().iloc[0])
    network = compute_pass_network(events, team)
    assert isinstance(network["nodes"], list)
    assert isinstance(network["edges"], list)
