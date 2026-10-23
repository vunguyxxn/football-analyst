from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from backend.cv.finetune_person import person_validator_class, verify_dataset
from backend.cv.prepare_person_dataset import convert_labels, partition, prepare, verify_source


def test_label_mapping_excludes_ball_and_clips_boundary_boxes():
    text, counts, clipped = convert_labels("0 .5 .5 .01 .01\n1 .5 .5 .1 .2\n2 .01 .5 .1 .2\n3 .7 .5 .1 .2\n")
    rows = [list(map(float, line.split())) for line in text.splitlines()]
    assert len(rows) == 3 and all(row[0] == 0 for row in rows)
    assert counts == {0: 1, 1: 1, 2: 1, 3: 1} and clipped == 1
    assert rows[1][1] == pytest.approx(.03) and rows[1][3] == pytest.approx(.06)


@pytest.mark.parametrize("line", ["4 .5 .5 .1 .1", "2 nan .5 .1 .1", "2 .5 .5 0 .1", "2 .5 .5 .1"])
def test_bad_annotations_fail_closed(line):
    with pytest.raises(ValueError):
        convert_labels(line)


def test_exact_and_near_duplicates_stay_in_same_split_and_seed_is_reproducible():
    records = [{"group": str(i), "pixel_sha256": str(i), "dhash": 1 << i,
                "thumbnail": np.full((2, 2), i * 20, dtype=np.uint8)} for i in range(7)]
    records[1]["pixel_sha256"] = records[0]["pixel_sha256"]
    records[3]["dhash"] = records[2]["dhash"]
    records[3]["thumbnail"] = records[2]["thumbnail"] + 1
    copy = deepcopy(records)
    audit = partition(records, 123)
    partition(copy, 123)
    assert audit["components"] == 5
    assert records[0]["split"] == records[1]["split"]
    assert records[2]["split"] == records[3]["split"]
    assert [r["split"] for r in records] == [r["split"] for r in copy]
    assert {r["split"] for r in records} == {"train", "val", "test"}


def test_source_blob_and_lfs_hashes_are_checked(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"abc")
    blob = hashlib.sha1(b"blob 3\0abc").hexdigest()
    verify_source(path, {"size": 3, "blobId": blob})
    verify_source(path, {"size": 3, "lfs": {"sha256": hashlib.sha256(b"abc").hexdigest()}})
    with pytest.raises(ValueError):
        verify_source(path, {"size": 3, "blobId": "wrong"})


def test_preparation_and_training_integrity_guard(tmp_path):
    import cv2
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "docs/fixtures/yolo_person_finetune_protocol.json").read_text())
    source = tmp_path / "raw"
    files = []
    for i in range(5):
        for kind, suffix, payload in (("images", ".jpg", None), ("labels", ".txt", "2 .5 .5 .1 .2\n")):
            relative = f"data/train/{kind}/{i:06x}_0_png.rf.test{suffix}"
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if payload is None:
                cv2.imwrite(str(path), np.full((32, 32, 3), i * 40, dtype=np.uint8))
            else:
                path.write_text(payload)
            data = path.read_bytes()
            files.append({"rfilename": relative, "size": len(data),
                          "blobId": hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()})
    output = tmp_path / "prepared"
    manifest = prepare(tmp_path, source, output, {"files": files}, protocol)
    assert sum(manifest["images"].values()) == 5
    assert verify_dataset(output)["images"] == manifest["images"]
    with pytest.raises(FileExistsError):
        prepare(tmp_path, source, output, {"files": files}, protocol)
    record = manifest["files"][0]
    (output / record["label"]).write_text("0 .5 .5 .9 .9\n")
    with pytest.raises(ValueError, match="hash/path"):
        verify_dataset(output)


def test_baseline_person_filter_happens_before_agnostic_nms(tmp_path, monkeypatch):
    monkeypatch.setenv("YOLO_CONFIG_DIR", str(tmp_path))
    import torch
    cls = person_validator_class()
    validator = object.__new__(cls)
    validator.args = SimpleNamespace(conf=.25, iou=.5, task="detect", max_det=300)
    validator.nc, validator.end2end = 2, False
    # Same anchor strongly predicts another class; it must not suppress person.
    prediction = torch.zeros((1, 6, 2))
    prediction[0, :4, 0] = torch.tensor([20, 20, 10, 10])
    prediction[0, 4:, 0] = torch.tensor([.8, .99])
    prediction[0, :4, 1] = torch.tensor([100, 100, 10, 10])
    prediction[0, 4:, 1] = torch.tensor([.1, .9])
    result = validator.postprocess(prediction)[0]
    assert result["cls"].tolist() == [0]
    assert result["conf"].tolist() == pytest.approx([.8])
