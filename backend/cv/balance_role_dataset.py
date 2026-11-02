"""Materialize reviewed train-only ROIs with capped, explicit sampling weights."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import NAMES, audit, verify_dataset, yaml_text
from backend.cv.validate_referee_annotations import validate


def repeat_count(region, policy):
    if region["review_status"] != "agent_reviewed":
        raise ValueError("Unreviewed ROI")
    if region["kind"] == "referee":
        count = policy["referee_color_repeats"][region["attributes"]["shirt_color"]]
    else:
        count = policy[region["kind"]+"_repeats"]
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= policy["maximum_repeats"] <= 6:
        raise ValueError("Sampling repeat outside locked cap")
    return count


def crop_labels(region):
    """Only ROI-contained reviewed boxes; never infer labels outside the ROI."""
    from backend.cv.validate_referee_annotations import box_inside
    x1, y1, x2, y2 = region["roi"]
    width, height = x2-x1, y2-y1
    if min(width, height) <= 0:
        raise ValueError("Empty crop")
    lines = []
    for obj in region["objects"]:
        box_inside(obj["xyxy"], region["roi"])
        a, b, c, d = obj["xyxy"]
        lines.append(f'{NAMES.index(obj["role"])} {((a+c)/2-x1)/width:.9f} {((b+d)/2-y1)/height:.9f} {(c-a)/width:.9f} {(d-b)/height:.9f}')
    return "\n".join(lines) + ("\n" if lines else "")


def protected_rows(manifest):
    return sorted((row["split"], row["image"], row["image_sha256"], row["label"], row["label_sha256"])
                  for row in manifest["files"] if row["split"] != "train")


def prepare(root, protocol_path, output):
    import cv2
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    base_protocol = checked(root, protocol["base_protocol"], protocol["base_protocol_sha256"])
    dataset = (root / protocol["base_dataset"]).resolve()
    if not dataset.is_relative_to(root):
        raise ValueError("Foreign dataset path")
    checked(dataset, "manifest.json", protocol["base_manifest_sha256"])
    original = verify_dataset(root, dataset, base_protocol)
    packet_path = checked(root, protocol["annotation_packet"], protocol["annotation_packet_sha256"])
    review = validate(root, packet_path, verify_assets=True)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in packet["sources"]}
    uncertain_images = {sources[item["source_id"]]["source_sha256"] for item in packet["quarantine"]
                        if sources[item["source_id"]]["type"] == "image"}
    excluded = [row for row in original["files"] if row["split"] == "train" and row["provenance"].get("image_sha256") in uncertain_images]
    if len(excluded) != protocol["expected_excluded_base_images"]:
        raise ValueError("Quarantine exclusion differs from locked protocol")
    rows = []
    output.mkdir(parents=True)
    for row in original["files"]:
        if row in excluded:
            continue
        for kind in ("image", "label"):
            target = output / row[kind]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checked(dataset, row[kind], row[kind+"_sha256"]), target)
        rows.append({**row, "sampling_origin": "base_full_frame", "sampling_repeat": 1})
    # Only one decoded source image/frame retained at a time.
    for source in packet["sources"]:
        path = checked(root, source["source"])
        if source["type"] == "image":
            image = cv2.imread(str(path))
        else:
            cap = cv2.VideoCapture(str(path))
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, source["frame"])
                ok, image = cap.read()
                if not ok:
                    raise ValueError("Cannot decode reviewed training frame")
            finally:
                cap.release()
        for region in packet["regions"]:
            if region["source_id"] != source["id"]:
                continue
            x1, y1, x2, y2 = region["roi"]
            patch = image[y1:y2, x1:x2]
            encoded = cv2.imencode(".png", patch)[1].tobytes()
            if hashlib.sha256(encoded).hexdigest() != region["patch_sha256"]:
                raise ValueError("Reviewed crop changed")
            label = crop_labels(region)
            pixel_hash = hashlib.sha256(str(patch.shape).encode()+patch.tobytes()).hexdigest()
            count = repeat_count(region, protocol["sampling"])
            for index in range(count):
                stem = f'roi-{region["id"]}-repeat{index+1}'
                image_rel, label_rel = f"images/train/{stem}.png", f"labels/train/{stem}.txt"
                (output / image_rel).write_bytes(encoded)
                (output / label_rel).write_text(label, encoding="utf-8")
                rows.append({"image": image_rel, "label": label_rel, "image_sha256": digest(output / image_rel),
                             "label_sha256": digest(output / label_rel), "pixel_sha256": pixel_hash,
                             "family": source["family"], "split": "train", "source": source["source_sha256"],
                             "provenance": {"annotation_region": region["id"], "roi": region["roi"], "source_id": source["id"]},
                             "sampling_origin": "reviewed_roi", "sampling_repeat": index+1, "sampling_weight": count,
                             "class_counts": dict(Counter(int(line.split()[0]) for line in label.splitlines()))})
    audit(rows)
    manifest = {"kind": "role_balanced_dataset_v2", "protocol_sha256": digest(protocol_path), "names": NAMES,
                "images": dict(Counter(row["split"] for row in rows)), "files": rows,
                "excluded_base_images": [{"image": row["image"], "image_sha256": row["image_sha256"]} for row in excluded],
                "reviewed_roi_units": review["regions"], "referee_observations_new": review["new_local_referees"],
                "referee_observations_reviewed_existing": review["reviewed_existing_referees"],
                "limitation": "Repeated ROI exposures are not new independent examples. Old val/test sources unchanged and previously inspected; no independent match validation."}
    if protected_rows(original) != protected_rows(manifest):
        raise ValueError("Validation/test files changed")
    (output / "data.yaml").write_text(yaml_text(output), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verify_dataset(root, output, protocol_path)
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
