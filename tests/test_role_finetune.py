from collections import Counter
import json
from types import SimpleNamespace

import pytest

from backend.cv.evaluate_role_detector import digest
from backend.cv.finetune_roles import metric_report
from backend.cv.prepare_role_dataset import NAMES, audit, convert_roles, prepare, verify_dataset, yaml_text


def test_conversion_retains_keeper_and_referee_separately_and_drops_ball():
    text = "0 .5 .5 .1 .1\n1 .2 .3 .1 .2\n2 .4 .5 .1 .2\n3 .6 .7 .1 .2\n"
    rows = convert_roles(text).splitlines()
    assert [row.split()[0] for row in rows] == ["1", "0", "2"]
    assert len(rows) == 3


@pytest.mark.parametrize("change", [{"target_names": ["goalkeeper", "player", "referee"]},
                                  {"source_mapping": {"0": None, "1": 0, "2": 0, "3": 0}}])
def test_protocol_cannot_silently_swap_or_merge_roles(tmp_path, change):
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"target_names": NAMES, "source_mapping": {"0": None, "1": 1, "2": 0, "3": 2}} | change))
    with pytest.raises(ValueError, match="conversion policy"):
        prepare(tmp_path, protocol, tmp_path / "output")


@pytest.mark.parametrize("line", ["4 .5 .5 .1 .1", "1 nan .5 .1 .1", "3 .5 .5 -.1 .1"])
def test_role_conversion_rejects_corrupt_source_labels(line):
    with pytest.raises(ValueError):
        convert_roles(line)


@pytest.mark.parametrize("key", ["family", "source", "pixel_sha256"])
def test_family_source_or_pixels_cannot_leak_between_splits(key):
    rows = [{"split": split, "family": split, "source": split, "pixel_sha256": split} for split in ["train", "val", "test"]]
    audit(rows)
    rows[1][key] = rows[0][key]
    with pytest.raises(ValueError, match="leakage"):
        audit(rows)


def test_metrics_match_native_role_ids_even_if_a_class_has_no_positive():
    box = SimpleNamespace(map50=.5, map=.3, ap_class_index=[0, 2], class_result=lambda i: [.8, .7, .6, .4] if i == 0 else [.2, .1, .4, .2])
    result = metric_report(SimpleNamespace(box=box))
    assert result["classes"]["referee"]["map50_95"] == .2
    assert result["classes"]["goalkeeper"]["map50_95"] == 0


def test_prepared_dataset_hash_and_yaml_are_required(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    protocol = tmp_path / "protocol.json"
    protocol.write_text("{}")
    rows = []
    for split in ["train", "val", "test"]:
        image, label = dataset / (split+".png"), dataset / (split+".txt")
        image.write_bytes(split.encode())
        label.write_text("0 .5 .5 .2 .2\n")
        rows.append({"split": split, "family": split, "source": split, "pixel_sha256": split,
                     "image": image.name, "label": label.name, "image_sha256": digest(image), "label_sha256": digest(label)})
    (dataset / "manifest.json").write_text(json.dumps({"protocol_sha256": digest(protocol), "names": NAMES, "files": rows}))
    (dataset / "data.yaml").write_text(yaml_text(dataset))
    verify_dataset(tmp_path, dataset, protocol)
    (dataset / "train.txt").write_text("2 .5 .5 .2 .2\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_dataset(tmp_path, dataset, protocol)
