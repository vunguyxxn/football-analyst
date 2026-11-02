import json

import pytest

from backend.cv.evaluate_role_detector import checked, digest, load_samples, match, summarize


def test_matching_is_role_blind_and_one_to_one():
    labels = [{"role": "referee", "xyxy": [0, 0, 10, 20]},
              {"role": "player", "xyxy": [1, 0, 11, 20]}]
    predictions = [{"role": "player", "xyxy": [0, 0, 10, 20]}]
    rows = match(labels, predictions)
    assert rows[0]["prediction"]["role"] == "player"
    assert rows[1]["prediction"] is None
    report = summarize(rows)
    assert report["nonplayers_predicted_player"] == 1
    assert report["classes"]["referee"]["correct_fraction_of_labels"] == 0
    assert report["precision"] is None and report["mAP"] is None


def test_foot_gate_and_box_iou_apply_independently():
    prediction = [{"role": "goalkeeper", "xyxy": [0, 0, 20, 40]}]
    assert match([{"role": "goalkeeper", "xy": [10, 65]}], prediction, foot_gate=25)[0]["prediction"]
    assert match([{"role": "goalkeeper", "xy": [10, 65.1]}], prediction, foot_gate=25)[0]["prediction"] is None
    assert match([{"role": "goalkeeper", "xyxy": [200, 0, 220, 40]}], prediction)[0]["prediction"] is None


def test_misses_and_unlabelled_predictions_do_not_become_precision():
    rows = match([{"role": "referee", "xy": [50, 50]}, {"role": "outside", "xy": [0, 0]}], [])
    result = summarize(rows)
    assert result["classes"]["referee"]["predicted"] == {"missed": 1}
    assert result["nonplayer_labels"] == 1
    assert result["classes"]["goalkeeper"]["correct_fraction_of_labels"] is None


def test_source_and_label_hashes_fail_closed(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    fixture = tmp_path / "labels.json"
    fixture.write_text(json.dumps({"source_sha256": digest(source), "frames": [0],
                                   "labels": [{"frame": 0, "role": "white_outfield", "xyxy": [0, 0, 5, 10]}]}))
    protocol = {"datasets": [{"format": "context_boxes", "source": source.name, "fixture": fixture.name,
                               "fixture_sha256": digest(fixture)}]}
    assert load_samples(tmp_path.resolve(), protocol)[0]["labels"][0]["role"] == "player"
    source.write_bytes(b"replaced")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_samples(tmp_path.resolve(), protocol)
    with pytest.raises(ValueError, match="hash mismatch"):
        checked(tmp_path.resolve(), fixture.name, "wrong")
    with pytest.raises(ValueError, match="outside-workspace"):
        checked(tmp_path.resolve(), "../AGENTS.md")
