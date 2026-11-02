"""Prepare three-role labels with conservative visual-source family splits."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_person_dataset import convert_labels, verify_source

NAMES = ["player", "goalkeeper", "referee"]
SOURCE_MAPPING = {1: 1, 2: 0, 3: 2}


def convert_roles(text):
    # Reuse strict normalized-source validation, but do not merge roles.
    convert_labels(text)
    converted = []
    for line in text.splitlines():
        if not line.strip():
            continue
        cls, *coordinates = line.split()
        cls = int(cls)
        if cls == 0:
            continue
        x, y, w, h = map(float, coordinates)
        x1, y1, x2, y2 = max(0., x-w/2), max(0., y-h/2), min(1., x+w/2), min(1., y+h/2)
        converted.append(f"{SOURCE_MAPPING[cls]} {(x1+x2)/2:.9f} {(y1+y2)/2:.9f} {x2-x1:.9f} {y2-y1:.9f}")
    return "\n".join(converted) + ("\n" if converted else "")


def yaml_text(output):
    return (f"path: {json.dumps(output.as_posix())}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n"
            + "".join(f"  {i}: {name}\n" for i, name in enumerate(NAMES)))


def audit(records):
    seen = {key: {} for key in ("family", "source", "pixel_sha256")}
    for row in records:
        for key, lookup in seen.items():
            value = row[key]
            if value in lookup and lookup[value] != row["split"]:
                raise ValueError(f"Cross-split leakage: {key}")
            lookup[value] = row["split"]
    if {row["split"] for row in records} != {"train", "val", "test"}:
        raise ValueError("Need three nonempty splits")


def prepare(root, protocol_path, output):
    import cv2
    import hashlib
    import numpy as np
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol["target_names"] != NAMES or protocol["source_mapping"] != {"0": None, "1": 1, "2": 0, "3": 2}:
        raise ValueError("Unsupported role conversion policy")
    inventory = json.loads(checked(root, protocol["inventory"], protocol["inventory_sha256"]).read_text())
    if inventory["revision"] != protocol["source_revision"]:
        raise ValueError("Source revision mismatch")
    labels_path = checked(root, protocol["local_annotations"], protocol["local_annotations_sha256"])
    local = json.loads(labels_path.read_text(encoding="utf-8"))
    source_root = root / "data/raw/football_detection_source_v1"
    specs = {spec["rfilename"]: spec for spec in inventory["files"]}
    records = []

    def record(image, converted, *, name, family, split, source, provenance):
        if image is None:
            raise ValueError("Unreadable image")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        return {"name": name, "family": family, "split": split, "source": source,
                "pixel_sha256": hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest(),
                "dhash": sum(int(v) << i for i, v in enumerate((small[:, 1:] > small[:, :-1]).flat)),
                "thumbnail": cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA),
                "converted": converted, "provenance": provenance}

    for name, spec in sorted(specs.items()):
        if "/images/" not in name or not name.endswith(".jpg"):
            continue
        label = name.replace("/images/", "/labels/").replace(".jpg", ".txt")
        image_path, label_path = checked(source_root, name), checked(source_root, label)
        verify_source(image_path, spec)
        verify_source(label_path, specs[label])
        prefix = Path(name).name.split("_")[0]
        family = protocol["prefix_families"][prefix]
        records.append(record(cv2.imread(str(image_path)), convert_roles(label_path.read_text()),
                              name=Path(name).stem, family=family, split=protocol["family_splits"][family],
                              source=f"external:{prefix}", provenance={"image": name, "image_sha256": digest(image_path),
                              "label": label, "label_sha256": digest(label_path)}))
    source_hashes = {}
    for frame in local["frames"]:
        path = checked(root, frame["source"])
        if str(path) not in source_hashes:
            source_hashes[str(path)] = digest(path)
        if source_hashes[str(path)] != frame["source_sha256"]:
            raise ValueError("Local video hash mismatch")
        family = protocol["local_families"][Path(frame["source"]).name]
        if frame["split"] != protocol["family_splits"][family]:
            raise ValueError("Local label split differs from locked family")
        cap = cv2.VideoCapture(str(path))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame["frame"])
            ok, image = cap.read()
            if not ok or image.shape[:2] != (frame["height"], frame["width"]):
                raise ValueError("Local frame decode/shape mismatch")
        finally:
            cap.release()
        # Fixture binds the exact lossless PNG inspected by the annotator.
        encoded = cv2.imencode(".png", image)[1].tobytes()
        if hashlib.sha256(encoded).hexdigest() != frame["raw_image_sha256"]:
            raise ValueError("Reviewed frame pixels changed")
        converted = []
        for person in frame["people"]:
            x1, y1, x2, y2 = person["xyxy"]
            if not all(math.isfinite(v) for v in (x1, y1, x2, y2)) or not (0 <= x1 < x2 <= frame["width"] and 0 <= y1 < y2 <= frame["height"]):
                raise ValueError("Invalid reviewed box")
            converted.append(f'{NAMES.index(person["role"])} {(x1+x2)/2/frame["width"]:.9f} {(y1+y2)/2/frame["height"]:.9f} {(x2-x1)/frame["width"]:.9f} {(y2-y1)/frame["height"]:.9f}')
        records.append(record(image, "\n".join(converted)+"\n", name="local-"+frame["key"], family=family,
                              split=frame["split"], source=frame["source_sha256"],
                              provenance={"video": frame["source"], "video_sha256": frame["source_sha256"], "frame": frame["frame"]}))
    audit(records)
    # Fail rather than quietly send duplicate/near-duplicate pixels to another split.
    for i, a in enumerate(records):
        for b in records[:i]:
            if a["split"] != b["split"] and (a["dhash"] ^ b["dhash"]).bit_count() <= 4 and float(np.abs(a["thumbnail"].astype(float)-b["thumbnail"]).mean()) <= 3:
                raise ValueError("Cross-split near-duplicate")
    output.mkdir(parents=True)
    manifest_rows, emitted = [], {}
    for row in records:
        if row["pixel_sha256"] in emitted:
            if emitted[row["pixel_sha256"]] != row["converted"]:
                raise ValueError("Duplicate pixels have conflicting role labels")
            continue
        emitted[row["pixel_sha256"]] = row["converted"]
        image_path = output / "images" / row["split"] / (row["name"]+".png")
        label_path = output / "labels" / row["split"] / (row["name"]+".txt")
        image_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.parent.mkdir(parents=True, exist_ok=True)
        if "video" in row["provenance"]:
            cap = cv2.VideoCapture(str(root / row["provenance"]["video"]))
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, row["provenance"]["frame"])
                ok, image = cap.read()
                if not ok:
                    raise ValueError("Local frame unavailable")
            finally:
                cap.release()
        else:
            image = cv2.imread(str(source_root / row["provenance"]["image"]))
        cv2.imwrite(str(image_path), image)
        label_path.write_text(row["converted"], encoding="utf-8")
        manifest_rows.append({k: v for k, v in row.items() if k not in {"dhash", "thumbnail", "converted", "name"}} |
                             {"image": image_path.relative_to(output).as_posix(), "label": label_path.relative_to(output).as_posix(),
                              "image_sha256": digest(image_path), "label_sha256": digest(label_path),
                              "class_counts": dict(Counter(int(line.split()[0]) for line in row["converted"].splitlines()))})
    (output / "data.yaml").write_text(yaml_text(output), encoding="utf-8")
    manifest = {"kind": "role_dataset_v1", "protocol_sha256": digest(protocol_path), "images": dict(Counter(row["split"] for row in manifest_rows)),
                "names": NAMES, "files": manifest_rows, "limitation": "Visual source families, not independently verified match identities; model-assisted local boxes reviewed by one agent."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify_dataset(root, dataset, protocol_path):
    manifest = json.loads((dataset / "manifest.json").read_text())
    if manifest["protocol_sha256"] != digest(protocol_path) or manifest["names"] != NAMES or (dataset / "data.yaml").read_text() != yaml_text(dataset):
        raise ValueError("Dataset protocol or class map changed")
    audit(manifest["files"])
    for row in manifest["files"]:
        for key in ("image", "label"):
            checked(dataset, row[key], row[key+"_sha256"])
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if not args.output.resolve().is_relative_to(root):
        raise ValueError("Output must stay in workspace")
    print(json.dumps(prepare(root, checked(root, args.protocol), args.output.resolve())["images"]))
