import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from backend.tactics.metrica_game3 import load_window, read_metadata, role_reference


FIXTURES = Path(__file__).resolve().parents[1] / "docs/fixtures"


@pytest.fixture
def metadata():
    return read_metadata(FIXTURES / "metrica_game3_metadata.xml")


def test_pinned_provider_metadata_and_two_levels_of_role_layout(metadata):
    source = json.loads((FIXTURES / "metrica_game3_sources.json").read_text())
    spec = next(s for s in source["files"] if s["filename"].endswith('.xml'))
    assert hashlib.sha256((FIXTURES / "metrica_game3_metadata.xml").read_bytes()).hexdigest() == spec["sha256"]
    assert metadata["fps"] == 25
    assert metadata["directions_first_half"] == {"A": -1, "B": 1}
    assert len(metadata["players"]) == 35 and len(metadata["formats"]) == 11
    a, b = [role_reference(metadata, team, 1, 250) for team in ("A", "B")]
    assert (a["coarse_shape"], a["role_depth_shape"], a["goalkeeper_id"]) == ("4-5-1", "4-2-3-1", 11)
    assert (b["coarse_shape"], b["role_depth_shape"], b["goalkeeper_id"]) == ("4-4-2", "4-4-2", 1028)
    assert a["is_frame_tactical_ground_truth"] is False


def test_channel_ordinal_is_not_shirt_number_and_coordinates_are_converted(metadata):
    tracks, audit = load_window(FIXTURES / "metrica_game3_tracking_excerpt.txt", metadata, 1, 0, .12)
    lookup = {t.track_id: t for t in tracks}
    assert audit["native_frames"] == 3 and len(tracks) == 22
    # The first tracking pair is channel player1_x/y -> source P3578 -> shirt 11.
    assert lookup[11].xy[0].tolist() == pytest.approx([.84722 * 105, (1 - .52855) * 68])
    assert lookup[1].xy[0].tolist() == pytest.approx([.65268 * 105, (1 - .24792) * 68])
    assert lookup[11].times.tolist() == pytest.approx([0, .04, .08])
    assert lookup[1028].team == "B"


def test_period_relative_clock_and_source_roster_boundary(metadata):
    tracks, audit = load_window(FIXTURES / "metrica_game3_tracking_excerpt.txt", metadata, 2, 0, .08)
    assert audit["native_frames"] == 2
    assert tracks[0].frames.tolist() == [69662, 69663]
    assert tracks[0].times.tolist() == [0, .04]
    assert role_reference(metadata, "A", 89697, 89698)["reason"] == "window_crosses_roster_boundary"
    before = role_reference(metadata, "A", 89697, 89697)
    after = role_reference(metadata, "A", 89698, 89698)
    assert 9 in {p["track_id"] for p in before["players"]}
    assert 9 not in {p["track_id"] for p in after["players"]}
    assert 14 in {p["track_id"] for p in after["players"]}


@pytest.mark.parametrize("fault", ["duplicate_player", "wrong_channel_axis", "overlapping_formats", "wrong_pitch"])
def test_invalid_metadata_fails_closed(tmp_path, fault):
    tree = ET.parse(FIXTURES / "metrica_game3_metadata.xml")
    root = tree.getroot()
    if fault == "duplicate_player":
        players = root.findall('./Metadata/Players/Player')
        players[1].find('ShirtNumber').text = players[0].findtext('ShirtNumber')
    elif fault == "wrong_channel_axis":
        root.find('./Metadata/PlayerChannels/PlayerChannel').set('channelId', 'y')
    elif fault == "overlapping_formats":
        root.findall('./DataFormatSpecifications/DataFormatSpecification')[1].set('startFrame', '1')
    else:
        root.find('./Metadata/Sessions/Session/FieldSize/Width').text = '110'
    path = tmp_path / 'bad.xml'
    tree.write(path)
    with pytest.raises(ValueError):
        read_metadata(path)


def test_bad_tracking_and_out_of_period_requests(metadata, tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_text('1:0.5,0.5:NaN,NaN\n2:0.5,0.5:NaN,NaN\n')
    with pytest.raises(ValueError, match="column count"):
        load_window(path, metadata, 1, 0, 1)
    with pytest.raises(ValueError, match="inside"):
        load_window(path, metadata, 1, 0, 10000)


def test_missing_outside_points_and_native_frame_gap_are_preserved(metadata, tmp_path):
    lines = (FIXTURES / 'metrica_game3_tracking_excerpt.txt').read_text().splitlines()[:3]
    parts = lines[1].split(':')
    samples = parts[1].split(';')
    samples[0], samples[1] = 'NaN,NaN', '1.2,0.5'
    parts[1] = ';'.join(samples)
    lines[1] = ':'.join(parts)
    path = tmp_path / 'gaps.txt'
    path.write_text('\n'.join(lines)+'\n')
    tracks, audit = load_window(path, metadata, 1, 0, .12)
    assert audit['missing'] == audit['outside'] == 1
    keeper = next(t for t in tracks if t.track_id == 11)
    assert keeper.frames.tolist() == [1, 3]
    assert keeper.segments.tolist() == [0, 1]
