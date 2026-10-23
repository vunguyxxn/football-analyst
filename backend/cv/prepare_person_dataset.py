"""Pinned source download, annotation conversion and group-disjoint partition."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import time


def canonical_path(path):
    value = str(Path(path).resolve())
    # Windows may return the extended drive prefix during concurrent mkdir.
    # Normalize only drive paths, retaining resolved symlink targets/checks.
    if value.startswith("\\\\?\\") and len(value) > 6 and value[5] == ":":
        value = value[4:]
    return Path(value)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dataset_yaml(path):
    return f"path: {json.dumps(path.as_posix())}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\n"


def verify_source(path, spec):
    data = Path(path).read_bytes()
    if len(data) != spec["size"]:
        raise ValueError("Source size mismatch")
    if spec.get("lfs"):
        valid = hashlib.sha256(data).hexdigest() == spec["lfs"]["sha256"]
    else:
        valid = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == spec["blobId"]
    if not valid:
        raise ValueError("Pinned source content hash mismatch")


def convert_labels(text):
    """Merge keeper/player/referee to person, exclude ball; clip edge boxes."""
    lines, original, clipped = [], Counter(), 0
    for line in text.splitlines():
        if not line.strip():
            continue
        cells = line.split()
        if len(cells) != 5 or cells[0] not in ("0", "1", "2", "3"):
            raise ValueError("Unsupported YOLO annotation")
        cls = int(cells[0])
        x, y, w, h = map(float, cells[1:])
        if not all(math.isfinite(v) for v in (x, y, w, h)) or not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            raise ValueError("Invalid normalized annotation")
        original[cls] += 1
        if cls == 0:
            continue
        x1, y1, x2, y2 = max(0., x - w / 2), max(0., y - h / 2), min(1., x + w / 2), min(1., y + h / 2)
        clipped += int(x - w / 2 < 0 or y - h / 2 < 0 or x + w / 2 > 1 or y + h / 2 > 1)
        lines.append(f"0 {(x1+x2)/2:.9f} {(y1+y2)/2:.9f} {x2-x1:.9f} {y2-y1:.9f}")
    return "\n".join(lines) + ("\n" if lines else ""), dict(original), clipped


def partition(records, seed):
    """Union related frames before assigning complete components to splits."""
    import numpy as np
    parent = {r["group"]: r["group"] for r in records}
    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    near_pairs = 0
    for i, a in enumerate(records):
        for b in records[:i]:
            if a["pixel_sha256"] == b["pixel_sha256"]:
                union(a["group"], b["group"])
            elif (a["dhash"] ^ b["dhash"]).bit_count() <= 4 and float(np.abs(a["thumbnail"].astype(float) - b["thumbnail"]).mean()) <= 3:
                union(a["group"], b["group"])
                near_pairs += 1
    groups = sorted({find(r["group"]) for r in records},
                    key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    if len(groups) < 5:
        raise ValueError("Too few independent filename/duplicate components for three splits")
    n_val = n_test = max(1, round(.2 * len(groups)))
    mapping = {key: "test" if i < n_test else "val" if i < n_test + n_val else "train"
               for i, key in enumerate(groups)}
    for record in records:
        record["component"] = find(record["group"])
        record["split"] = mapping[record["component"]]
    return {"components": len(groups), "near_duplicate_pairs": near_pairs,
            "split_components": dict(Counter(mapping.values()))}


def download(root, inventory, protocol):
    import requests
    source = canonical_path(root / "data/raw/football_detection_source_v1")
    by_name = {s["rfilename"]: s for s in inventory["files"]}
    names = [n for n in by_name if "/images/" in n and n.endswith(".jpg")]
    names += [n.replace("/images/", "/labels/").replace(".jpg", ".txt") for n in names]
    names += ["README.md", "data/README.roboflow.txt", "data/data.yaml"]
    def fetch(name):
        target = canonical_path(source / name)
        if not target.is_relative_to(source):
            raise ValueError(f"Foreign source path: {target} outside {source}")
        spec = by_name[name]
        if target.exists():
            verify_source(target, spec)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/datasets/{inventory['repo']}/resolve/{inventory['revision']}/{name}"
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=(15, 45))
                response.raise_for_status()
                partial = target.with_suffix(target.suffix + ".download")
                partial.write_bytes(response.content)
                verify_source(partial, spec)
                partial.replace(target)
                return
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1)
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, _ in enumerate(executor.map(fetch, names), 1):
            if i % 100 == 0:
                print(f"verified downloads {i}/{len(names)}", flush=True)
    return source


def prepare(root, source, output, inventory, protocol):
    import cv2
    if output.exists():
        raise FileExistsError(output)
    if protocol["mapping"] != {"0": None, "1": 0, "2": 0, "3": 0} or protocol["near_duplicate_dhash_max"] != 4 or protocol["near_duplicate_thumbnail_mae_max"] != 3 or protocol["group_ratios"] != [.6, .2, .2]:
        raise ValueError("Preparation policy differs from protocol")
    records, seen_pixels, exact_duplicates = [], {}, 0
    by_name = {s["rfilename"]: s for s in inventory["files"]}
    for name in sorted(by_name):
        if "/images/" not in name or not name.endswith(".jpg"):
            continue
        group = Path(name).name.split("_")[0]
        if not re.fullmatch("[0-9a-f]{6}", group):
            raise ValueError("Unknown filename grouping convention")
        label = name.replace("/images/", "/labels/").replace(".jpg", ".txt")
        verify_source(source / name, by_name[name])
        verify_source(source / label, by_name[label])
        image = cv2.imread(str(source / name))
        if image is None:
            raise ValueError("Unreadable source image")
        pixel_hash = hashlib.sha256(str(image.shape).encode() + image.tobytes()).hexdigest()
        converted, counts, clipped = convert_labels((source / label).read_text(encoding="utf-8"))
        if pixel_hash in seen_pixels:
            if seen_pixels[pixel_hash] != converted:
                raise ValueError("Identical pixels have inconsistent annotations")
            exact_duplicates += 1
        seen_pixels[pixel_hash] = converted
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        dhash = sum(int(v) << i for i, v in enumerate((small[:, 1:] > small[:, :-1]).flat))
        records.append({"source_image": name, "source_label": label, "group": group,
                        "pixel_sha256": pixel_hash, "dhash": dhash,
                        "thumbnail": cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA),
                        "converted": converted, "source_class_counts": counts, "clipped_boxes": clipped,
                        "image_sha256": sha256(source / name), "source_label_sha256": sha256(source / label)})
    audit = partition(records, protocol["split_seed"])
    output.mkdir(parents=True)
    emitted, manifest_rows = set(), []
    for record in records:
        if record["pixel_sha256"] in emitted:
            continue
        emitted.add(record["pixel_sha256"])
        split, filename = record["split"], Path(record["source_image"]).name
        image_path = output / "images" / split / filename
        label_path = output / "labels" / split / (Path(filename).stem + ".txt")
        image_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / record["source_image"], image_path)
        label_path.write_text(record["converted"], encoding="utf-8")
        manifest_rows.append({k: v for k, v in record.items() if k not in ("thumbnail", "converted", "dhash")}
                              | {"image": image_path.relative_to(output).as_posix(),
                                 "label": label_path.relative_to(output).as_posix(), "label_sha256": sha256(label_path)})
    counts = dict(Counter(r["split"] for r in manifest_rows))
    if set(counts) != {"train", "val", "test"}:
        raise ValueError("Every split needs images")
    (output / "data.yaml").write_text(dataset_yaml(output), encoding="utf-8")
    manifest = {"kind": "football_person_dataset_v1", "protocol": protocol, "images": counts,
                "source_images": len(records), "exact_duplicates_removed": exact_duplicates,
                "group_audit": audit, "files": manifest_rows,
                "limitation": "Filename/duplicate groups are heuristics, not verified disjoint matches; provided labels not independently re-annotated"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"images": counts, "group_audit": audit}), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if not output.is_relative_to(root) or output.exists():
        parser.error("Output must be a new directory inside project")
    protocol = json.loads((root / "docs/fixtures/yolo_person_finetune_protocol.json").read_text())
    inventory = json.loads((root / "docs/fixtures/football_detection_inventory.json").read_text())
    if (inventory["repo"], inventory["revision"]) != (protocol["source_repo"], protocol["source_revision"]):
        parser.error("Source revision mismatch")
    source = download(root, inventory, protocol) if args.download else root / "data/raw/football_detection_source_v1"
    prepare(root, source, output, inventory, protocol)


if __name__ == "__main__":
    main()
