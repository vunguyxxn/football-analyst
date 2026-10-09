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
