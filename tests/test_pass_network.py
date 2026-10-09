import pandas as pd

from backend.tactics.pass_network import compute_pass_network


def _sample_events() -> pd.DataFrame:
    rows = []
    for _ in range(3):
        rows.append(
            {
                "minute": 10,
                "team": "Home",
                "player": "A",
                "event_type": "Pass",
                "x_m": 20,
                "y_m": 30,
                "pass_outcome": None,
                "pass_recipient": "B",
            }
        )
    rows.extend(
        [
            {
                "minute": 11,
                "team": "Home",
                "player": "A",
                "event_type": "Pass",
                "x_m": 30,
                "y_m": 40,
                "pass_outcome": "Incomplete",
                "pass_recipient": "B",
            },
            {
                "minute": 12,
                "team": "Home",
                "player": "B",
                "event_type": "Carry",
                "x_m": 40,
                "y_m": 50,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "minute": 13,
                "team": "Home",
                "player": "B",
                "event_type": "Pass",
                "x_m": 45,
                "y_m": 55,
                "pass_outcome": None,
                "pass_recipient": "A",
            },
            {
                "minute": 14,
                "team": "Home",
                "player": "A",
                "event_type": "Substitution",
                "x_m": 25,
                "y_m": 35,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "minute": 15,
                "team": "Home",
                "player": "Late player",
                "event_type": "Pass",
                "x_m": 50,
                "y_m": 50,
                "pass_outcome": None,
                "pass_recipient": "A",
            },
            {
                "minute": 10,
                "team": "Away",
                "player": "Away player",
                "event_type": "Pass",
                "x_m": 60,
                "y_m": 30,
                "pass_outcome": None,
                "pass_recipient": "Another away player",
            },
        ]
    )
    return pd.DataFrame(rows)


def test_compute_pass_network_filters_failed_and_low_count_edges() -> None:
    network = compute_pass_network(_sample_events(), team="Home")

    assert {node["player"] for node in network["nodes"]} == {"A", "B"}
    assert next(node for node in network["nodes"] if node["player"] == "A")[
        "pass_count"
    ] == 3
    assert network["edges"] == [{"source": "A", "target": "B", "count": 3}]


def test_compute_pass_network_can_include_edges_below_default_threshold() -> None:
    network = compute_pass_network(
        _sample_events(),
        team="Home",
        min_edge_count=1,
    )

    assert network["edges"] == [
        {"source": "A", "target": "B", "count": 3},
        {"source": "B", "target": "A", "count": 1},
    ]


def test_minute_range_replaces_substitution_cutoff() -> None:
    network = compute_pass_network(
        _sample_events(),
        team="Home",
        minute_range=(14, 15),
        min_edge_count=1,
    )

    assert [node["player"] for node in network["nodes"]] == ["A", "Late player"]


def test_short_names_prefer_nicknames_and_disambiguate_duplicate_surnames() -> None:
    events = pd.DataFrame(
        [
            {
                "team": "Home",
                "player": "Thiago Silva",
                "player_nickname": None,
                "event_type": "Pass",
                "x_m": 10,
                "y_m": 20,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "team": "Home",
                "player": "Rafael Silva",
                "player_nickname": None,
                "event_type": "Pass",
                "x_m": 20,
                "y_m": 30,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "team": "Home",
                "player": "Marcelo Júnior",
                "player_nickname": None,
                "event_type": "Pass",
                "x_m": 30,
                "y_m": 40,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "team": "Home",
                "player": "Roberto Júnior",
                "player_nickname": None,
                "event_type": "Pass",
                "x_m": 40,
                "y_m": 50,
                "pass_outcome": None,
                "pass_recipient": None,
            },
            {
                "team": "Home",
                "player": "Neymar da Silva Santos Junior",
                "player_nickname": "Neymar",
                "event_type": "Pass",
                "x_m": 50,
                "y_m": 60,
                "pass_outcome": None,
                "pass_recipient": None,
            },
        ]
    )

    network = compute_pass_network(events, team="Home", min_edge_count=1)
    short_names = {
        node["player"]: node["short_name"] for node in network["nodes"]
    }

    assert short_names == {
        "Thiago Silva": "T. Silva",
        "Rafael Silva": "R. Silva",
        "Marcelo Júnior": "M. Júnior",
        "Roberto Júnior": "R. Júnior",
        "Neymar da Silva Santos Junior": "Neymar",
    }
    assert len(set(short_names.values())) == len(short_names)
