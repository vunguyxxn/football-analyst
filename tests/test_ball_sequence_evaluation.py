import json

import pytest

from backend.cv.evaluate_ball_sequence import evaluate, match_events, run


def fixture(tmp_path):
    folder = tmp_path / "predictions"
    folder.mkdir()
    event = {"kind": "possible_pass", "status": "unverified", "start_s": .1, "end_s": .9, "group": "A"}
    report = {"source_sha256": "source", "person_job_id": "job", "frames": 50, "possible_passes": [event]}
    (folder / "report.json").write_text(json.dumps(report))
    rows = [{"frame": i, "time_s": i / 10, "ball": {"center_px": [20, 20]}} for i in range(50)]
    rows[1]["ball"] = None
    rows[2]["ball"] = {"center_px": [80, 80]}
    (folder / "ball.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
    protocol = {"source_sha256": "source", "person_job_id": "job", "frames": 50, "fps": 10,
                "image_size": [100, 100], "point_tolerance_px": 12, "sample_step_frames": 1,
                "point_windows_frames": [[0, 4]], "closed_event_windows_s": [[0, 5]],
                "event_start_tolerance_s": .5, "event_end_tolerance_s": .5}
    review = {"source_sha256": "source", "independently_validated": True,
              "points": [{"frame": i, "visibility": "visible" if i < 3 else "uncertain", "center_px": [20, 20] if i < 3 else None}
                         for i in range(4)],
              "events": [{"id": "reference", "kind": "pass", "status": "reviewed_likely", "group": "A", "start_s": .1, "end_s": .9}]}
    return folder, protocol, review, report, rows


def test_missing_wrong_point_and_uncertain_are_distinct_and_never_independent(tmp_path):
    folder, protocol, review, _, _ = fixture(tmp_path)
    result = evaluate(folder, protocol, review)
    points = result["point_diagnostic"]
    assert (points["tp"], points["fp"], points["fn"], points["uncertain_skipped"]) == (1, 1, 2, 1)
    assert [row["status"] for row in points["rows"]] == ["matched", "missed", "wrong_point", "uncertain_not_scored"]
    assert points["max_consecutive_missed_samples"] == 2
    assert result["independently_validated"] is False
    shots = result["event_diagnostic"]["shot"]
    assert shots["status"] == "not_implemented" and shots["recall"] is None and shots["fp"] is None


def test_duplicate_prediction_does_not_match_one_reference_twice(tmp_path):
    folder, protocol, review, report, _ = fixture(tmp_path)
    report["possible_passes"] *= 2
    (folder / "report.json").write_text(json.dumps(report))
    result = evaluate(folder, protocol, review)["event_diagnostic"]["pass"]
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 0)
    assert result["precision"] == .5 and result["recall"] == 1


def test_maximum_matching_recovers_from_closest_first_conflict():
    predictions = [{"group": "A", "start_s": .8, "end_s": 1.8}, {"group": "A", "start_s": .4, "end_s": 1.4}]
    references = [{"id": "a", "group": "A", "start_s": .7, "end_s": 1.7}, {"id": "b", "group": "A", "start_s": 1.1, "end_s": 2.1}]
    assert len(match_events(predictions, references, .4, .4)) == 2


def test_shot_and_pass_are_separate_and_wrong_group_does_not_match(tmp_path):
    folder, protocol, review, report, _ = fixture(tmp_path)
    report["event_classes"] = ["pass", "shot"]
    report["possible_shots"] = [{**report["possible_passes"][0], "kind": "possible_shot"}]
    report["possible_passes"][0]["group"] = "B"
    (folder / "report.json").write_text(json.dumps(report))
    result = evaluate(folder, protocol, review)["event_diagnostic"]
    assert result["pass"]["tp"] == 0 and result["pass"]["fp"] == result["pass"]["fn"] == 1
    assert result["shot"]["tp"] == 0 and result["shot"]["fp"] == 1 and result["shot"]["recall"] is None
    review["events"][0]["kind"] = "shot"
    assert evaluate(folder, protocol, review)["event_diagnostic"]["shot"]["tp"] == 1


@pytest.mark.parametrize("change", [
    {"source_sha256": "other"}, {"person_job_id": "other"}, {"frames": 51},
    {"point_tolerance_px": float("nan")}, {"sample_step_frames": 0},
    {"closed_event_windows_s": [[1, 6]]}, {"point_windows_frames": [[0, 51]]},
])
def test_bad_protocol_rejected(tmp_path, change):
    folder, protocol, review, _, _ = fixture(tmp_path)
    with pytest.raises(ValueError):
        evaluate(folder, {**protocol, **change}, review)


def test_no_dropping_scheduled_samples_or_partial_sequence(tmp_path):
    folder, protocol, review, _, rows = fixture(tmp_path)
    review["points"].pop()
    with pytest.raises(ValueError, match="All scheduled"):
        evaluate(folder, protocol, review)
    review["points"].append({"frame": 3, "visibility": "uncertain", "center_px": None})
    (folder / "ball.jsonl").write_text("\n".join(json.dumps(row) for row in rows[:-1]))
    with pytest.raises(ValueError, match="frame count"):
        evaluate(folder, protocol, review)


def test_known_absence_is_not_a_visible_miss_and_unknown_group_is_rejected(tmp_path):
    folder, protocol, review, report, _ = fixture(tmp_path)
    review["points"][1] = {"frame": 1, "visibility": "absent", "center_px": None}
    result = evaluate(folder, protocol, review)
    assert result["point_diagnostic"]["rows"][1]["status"] == "correct_absence"
    assert result["point_diagnostic"]["fn"] == 1
    report["possible_passes"][0]["group"] = "unknown"
    (folder / "report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="Invalid predicted"):
        evaluate(folder, protocol, review)


def test_straddling_window_is_unscored_and_identity_cannot_be_promoted(tmp_path):
    folder, protocol, review, report, _ = fixture(tmp_path)
    protocol["closed_event_windows_s"] = [[0, 1]]
    report["possible_passes"] = [{**report["possible_passes"][0], "end_s": 1.1}]
    (folder / "report.json").write_text(json.dumps(report))
    result = evaluate(folder, protocol, review)["event_diagnostic"]["pass"]
    assert result["predictions_outside_scope"] == result["fn"] == 1
    assert result["fp"] == 0 and result["precision"] is None


def test_cli_records_frozen_input_hashes_and_preserves_existing_output(tmp_path, monkeypatch):
    import backend.cv.evaluate_ball_sequence as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    folder, protocol, review, _, _ = fixture(tmp_path)
    protocol_path, review_path, output = (tmp_path / name for name in ("protocol.json", "review.json", "audit.json"))
    protocol_path.write_text(json.dumps(protocol))
    review_path.write_text(json.dumps(review))
    result = run(folder, protocol_path, review_path, output)
    assert set(result["input_sha256"]) == {"protocol", "review", "predictions", "sequence"}
    assert all(len(value) == 64 for value in result["input_sha256"].values())
    with pytest.raises(ValueError):
        run(folder, protocol_path, review_path, output)
