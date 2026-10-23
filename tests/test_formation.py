import csv
import json
import sys

import numpy as np
import pytest

from backend.cv.metrica_benchmark import Trajectory
from backend.tactics.formation import analyze_window, main, spatial_shape


def positions(counts=(4, 4, 2)):
    result = {11: [5., 34.]}
    for x, count in zip((25., 45., 65., 85.), counts):
        for y in np.linspace(10, 58, count):
            result[len(result)] = [x, float(y)]
    return result


@pytest.mark.parametrize("counts", [(4, 4, 2), (4, 3, 3), (4, 2, 3, 1), (3, 5, 2)])
def test_known_shapes_and_mirrored_direction(counts):
    points = positions(counts)
    first = spatial_shape(points, 11, 1)
    mirrored = {p: [105 - xy[0], 68 - xy[1]] for p, xy in points.items()}
    second = spatial_shape(mirrored, 11, -1)
    assert first["shape"] == second["shape"] == "-".join(map(str, counts))
    assert [g["track_ids"] for g in first["lines"]] == [g["track_ids"] for g in second["lines"]]
    assert sum(len(g["track_ids"]) for g in first["lines"]) == 10
    assert first["width_m"] == second["width_m"] == 48


def test_uncertainty_and_invalid_inputs():
    points = positions()
    points[5][0] = 30  # five-metre borderline gap, no forced formation
    assert spatial_shape(points, 11, 1)["reason"] == "borderline_line_separation"
    assert spatial_shape({}, 11, 1)["status"] == "unknown"
    with pytest.raises(ValueError):
        spatial_shape(positions(), 11, 0)
    points[5][0] = float("nan")
    with pytest.raises(ValueError):
        spatial_shape(points, 11, 1)


def trajectories():
    return [Trajectory(1, p, "A", np.arange(100), np.arange(100) / 10,
                       np.tile(xy, (100, 1)), np.zeros(100, dtype=int), 10.)
            for p, xy in positions().items()]


def test_joint_window_and_metrics():
    result = analyze_window(trajectories(), 0, 10, 11, 1)
    assert result["shape"] == "4-4-2"
    assert result["joint_coverage"] == 1
    assert result["depth_m"] == 40
    assert len(result["players"]) == 11
    assert sum(p["is_goalkeeper"] for p in result["players"]) == 1


def test_missing_changed_roster_and_joint_gaps_abstain():
    tracks = trajectories()
    assert analyze_window(tracks[:-1], 0, 10, 11, 1)["status"] == "unknown"
    tracks.append(Trajectory(1, 99, "A", np.array([1]), np.array([.1]),
                             np.array([[20., 20.]]), np.array([0]), 10.))
    assert analyze_window(tracks, 0, 10, 11, 1)["reason"] == "incomplete_or_changed_roster"
    tracks = trajectories()
    for i, t in enumerate(tracks):
        # Each player >90% covered; union of missing frames leaves <80% jointly.
        keep = np.arange(100) // 3 != i
        t.frames, t.times, t.xy = t.frames[keep], t.times[keep], t.xy[keep]
    assert analyze_window(tracks, 0, 10, 11, 1)["reason"] == "insufficient_joint_coverage"


def test_duplicate_and_mixed_team_rejected():
    tracks = trajectories()
    with pytest.raises(ValueError, match="Duplicate"):
        analyze_window(tracks + [tracks[0]], 0, 10, 11, 1)
    tracks[0].team = "B"
    with pytest.raises(ValueError, match="one team"):
        analyze_window(tracks, 0, 10, 11, 1)


def test_cli_csv_coordinates_provenance_and_no_overwrite(tmp_path, monkeypatch):
    source, output = tmp_path / "tracking.csv", tmp_path / "result.json"
    points = positions()
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Home"])
        writer.writerow([""])
        writer.writerow(["Period", "Frame", "Time [s]"] +
                        [v for p in points for v in (f"Player{p}", "")])
        for frame in range(100):
            writer.writerow([1, frame, frame / 10] +
                            [v for x, y in points.values() for v in (x / 105, 1 - y / 68)])
    monkeypatch.setattr(sys, "argv", ["formation", "--input", str(source), "--output", str(output),
                                    "--game", "1", "--team", "A", "--goalkeeper-id", "11",
                                    "--attack-direction", "1", "--start", "0", "--stop", "10"])
    main()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["windows"][0]["shape"] == "4-4-2"
    assert result["ground_truth_validated"] is False
    assert len(result["source_sha256"]) == 64
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert output.read_bytes() == before
