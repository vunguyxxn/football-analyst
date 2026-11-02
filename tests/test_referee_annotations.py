import json
from pathlib import Path

import pytest

from backend.cv.evaluate_role_detector import digest
from backend.cv.validate_referee_annotations import validate


@pytest.fixture
def packet_files(tmp_path):
    annotations = tmp_path / "docs/fixtures/local_role_annotations_v1.json"
    annotations.parent.mkdir(parents=True)
    annotations.write_text(json.dumps({"frames": [
        {"source": "data/raw/train.mp4", "source_sha256": "a"*64, "frame": 0},
        {"source": "data/raw/held.mp4", "source_sha256": "b"*64, "frame": 0}]}))
    protocol = tmp_path / "base.json"
    protocol.write_text(json.dumps({"local_annotations": str(annotations.relative_to(tmp_path)),
                                   "local_annotations_sha256": digest(annotations),
                                   "local_families": {"train.mp4": "training", "held.mp4": "heldout"},
                                   "prefix_families": {"000111": "training"},
                                   "family_splits": {"training": "train", "heldout": "test"}}))
    source = {"id": "frame", "source": "data/raw/train.mp4", "source_sha256": "a"*64,
              "type": "video_frame", "frame": 10, "width": 100, "height": 100, "family": "training", "split": "train"}
    region = {"id": "region", "source_id": "frame", "subject_id": "0", "roi": [8, 18, 22, 52],
              "kind": "referee", "origin": "new_local_frame", "review_status": "agent_reviewed",
              "coverage": "visible match targets inside ROI only; outside ROI unlabelled",
              "objects": [{"id": "0", "role": "referee", "xyxy": [10, 20, 20, 50]}],
              "attributes": {"shirt_color": "light_blue", "pose": "front", "occlusion": "none_visible",
                             "body_clipped_by_image": False, "height_at_imgsz640": 192.}}
    packet = {"kind": "referee_annotation_packet_v2", "independently_validated": False,
              "training_performed": False, "runtime_changed": False,
              "base_protocol": "base.json", "base_protocol_sha256": digest(protocol),
              "sources": [source], "regions": [region], "quarantine": []}
    path = tmp_path / "packet.json"
    return tmp_path, path, packet


def run_packet(files):
    root, path, packet = files
    path.write_text(json.dumps(packet))
    return validate(root, path)


def test_partial_roi_labels_are_not_complete_frame_training_labels(packet_files):
    result = run_packet(packet_files)
    assert result["new_local_referees"] == 1
    assert result["reviewed_existing_referees"] == 0
    assert result["full_frames_are_training_ready"] is False
    assert result["independently_validated"] is False


@pytest.mark.parametrize("box", [[10, 20, float("nan"), 50], [10, 20, 25, 50]])
def test_invalid_or_outside_roi_boxes_fail(packet_files, box):
    packet_files[2]["regions"][0]["objects"][0]["xyxy"] = box
    with pytest.raises(ValueError, match="box"):
        run_packet(packet_files)


def test_full_frame_background_claim_is_rejected(packet_files):
    packet_files[2]["regions"][0]["coverage"] = "whole frame complete"
    with pytest.raises(ValueError, match="ROI-only"):
        run_packet(packet_files)


def test_protected_source_cannot_be_moved_into_training(packet_files):
    packet_files[2]["sources"][0].update(source="data/raw/held.mp4", source_sha256="b"*64, family="heldout")
    with pytest.raises(ValueError, match="Protected"):
        run_packet(packet_files)


def test_renamed_heldout_video_still_fails_hash_family_check(packet_files):
    packet_files[2]["sources"][0]["source_sha256"] = "b"*64
    with pytest.raises(ValueError, match="locked source family"):
        run_packet(packet_files)


def test_previously_annotated_frame_cannot_count_as_new(packet_files):
    packet_files[2]["sources"][0]["frame"] = 0
    with pytest.raises(ValueError, match="Previously labelled"):
        run_packet(packet_files)


def test_quarantine_applies_to_context_objects_too(packet_files):
    packet = packet_files[2]
    packet["regions"][0]["objects"].append({"id": "1", "role": "player", "xyxy": [11, 21, 19, 49]})
    packet["quarantine"].append({"source_id": "frame", "subject_id": "1", "xyxy": [11, 21, 19, 49], "reason": "uncertain role"})
    with pytest.raises(ValueError, match="Quarantined"):
        run_packet(packet_files)


def test_agent_review_cannot_claim_independent_validation(packet_files):
    packet_files[2]["independently_validated"] = True
    with pytest.raises(ValueError, match="independent-validation"):
        run_packet(packet_files)


def test_role_swap_is_rejected(packet_files):
    packet_files[2]["regions"][0]["objects"][0]["role"] = "goalkeeper"
    with pytest.raises(ValueError, match="Primary role"):
        run_packet(packet_files)


def test_existing_source_review_cannot_be_counted_as_new(packet_files):
    packet_files[2]["sources"][0].update(type="image", source="data/raw/000111_frame.jpg")
    with pytest.raises(ValueError, match="Existing annotation"):
        run_packet(packet_files)


def test_source_replacement_fails_before_decoding(packet_files):
    root, path, packet = packet_files
    source = root / "data/raw/train.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"different video")
    path.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="Source bytes changed"):
        validate(root, path, verify_assets=True)


def test_committed_packet_metadata_and_scope():
    root = Path(__file__).resolve().parents[1]
    report = validate(root, root / "docs/fixtures/referee_annotations_v2.json")
    assert (report["new_local_referees"], report["reviewed_existing_referees"]) == (30, 17)
    assert (report["player_hard_negative_regions"], report["staff_background_regions"]) == (30, 6)
    assert report["quarantined"] == 7
    assert report["referee_shirt_colors"] == {"light_blue": 33, "yellow": 10, "red": 3, "black": 1}
