"""Audit new licensed ROI counterexamples without changing protected data or weights."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import zipfile

from backend.cv.balance_role_dataset import crop_labels
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import NAMES
from backend.cv.validate_referee_annotations import box_inside


def git_blob_sha(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def duplicate_hits(feature, references):
    """Perceptual screening only; not a proof of distinct match identity."""
    import numpy as np
    return [row["image"] for row in references
            if (feature["dhash"] ^ row["dhash"]).bit_count() <= 4
            and float(np.abs(feature["thumbnail"].astype(float)-row["thumbnail"]).mean()) <= 3.]


def image_feature(image):
    import cv2
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return {"dhash": sum(int(v) << i for i, v in enumerate((small[:, 1:] > small[:, :-1]).flat)),
            "thumbnail": cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)}


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def validate_region(region, source):
    if region["review_status"] != "agent_reviewed" or region["coverage"] != "Only this reviewed ROI; pixels outside ROI remain unlabelled.":
        raise ValueError("Unreviewed or unsupported full-frame label claim")
    roi = region["roi"]
    box_inside(roi, [0, 0, source["width"], source["height"]])
    if any(isinstance(v, bool) or not isinstance(v, int) for v in roi):
        raise ValueError("Integer ROI pixels required")
    margin = region["context_margin_px"]
    if isinstance(margin, bool) or not isinstance(margin, int) or not 32 <= margin <= 128:
        raise ValueError("Wider reviewed context required")
    box_inside(region["primary_source_xyxy"], [0, 0, source["width"], source["height"]])
    a, b, c, d = region["primary_source_xyxy"]
    expected = [max(0, math.floor(a)-margin), max(0, math.floor(b)-margin), min(source["width"], math.ceil(c)+margin), min(source["height"], math.ceil(d)+margin)]
    if roi != expected:
        raise ValueError("ROI differs from locked context extent")
    ids = set()
    for obj in region["objects"]:
        if obj["id"] in ids or obj["role"] not in NAMES:
            raise ValueError("Duplicate or unsupported target role")
        ids.add(obj["id"])
        box_inside(obj["xyxy"], roi)
    subject = next((o for o in region["objects"] if o["id"] == region["primary_id"]), None)
    if subject is None or subject["role"] != region["primary_role"]:
        raise ValueError("Primary role mismatch, including merged goalkeeper")
    for unknown in source["uncertain_boxes"]:
        if overlaps(roi, unknown["xyxy"]):
            raise ValueError("Uncertain context actor cannot become background")


def validate(root, packet_path, verify_assets=False, export=None):
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet["kind"] != "role_counterexamples_v3" or any(packet[key] is not False for key in ("independently_validated", "training_performed", "runtime_changed")):
        raise ValueError("Unsupported packet or training/independence claim")
    dataset = (root / packet["protected_dataset"]).resolve()
    if not dataset.is_relative_to(root):
        raise ValueError("Foreign protected reference path")
    manifest_path = checked(dataset, "manifest.json", packet["protected_manifest_sha256"])
    manifest = json.loads(manifest_path.read_text())
    providers = {p["id"]: p for p in packet["providers"]}
    sources = {s["id"]: s for s in packet["sources"]}
    if len(providers) != len(packet["providers"]) or len(sources) != len(packet["sources"]):
        raise ValueError("Duplicate provider/source registry")
    for provider in providers.values():
        if provider["license"] != "CC-BY-4.0" or len(provider["revision"]) != 40:
            raise ValueError("Unregistered license or unpinned provider")
    protected_families = {row["family"] for row in manifest["files"]}
    for source in sources.values():
        if source["provider"] not in providers or source["split"] != "train" or source["scene_family"] in protected_families:
            raise ValueError("Unregistered provider or protected source family")
        if source["media_kind"] != "real_match_broadcast" or "pes_" in source.get("origin_path", "").lower():
            raise ValueError("Simulation source not allowed in this packet")
    seen, units = set(), set()
    counts = Counter()
    for region in packet["regions"]:
        source = sources[region["source_id"]]
        if region["id"] in seen or (source["id"], region["primary_id"]) in units:
            raise ValueError("Duplicate observation")
        seen.add(region["id"])
        units.add((source["id"], region["primary_id"]))
        validate_region(region, source)
        counts[(region["primary_role"], region["primary_color"])] += 1
    if export and not verify_assets:
        raise ValueError("Cannot export unverified assets")
    if export and (export.exists() or not export.resolve().is_relative_to(root)):
        raise ValueError("Export must be a new workspace directory")
    exported = []
    if verify_assets:
        import cv2
        references = []
        old_pixels = {row["pixel_sha256"] for row in manifest["files"]}
        old_files = {row["image_sha256"] for row in manifest["files"]}
        for row in manifest["files"]:
            checked(dataset, row["label"], row["label_sha256"])
            image = cv2.imread(str(checked(dataset, row["image"], row["image_sha256"])))
            references.append({"image": row["image"], **image_feature(image)})
        for provider in providers.values():
            proof = checked(root, provider["license_file"], provider["license_sha256"])
            if provider.get("license_git_blob_sha") and git_blob_sha(proof.read_bytes()) != provider["license_git_blob_sha"]:
                raise ValueError("License proof Git blob mismatch")
            if provider.get("archive"):
                checked(root, provider["archive"], provider["archive_sha256"])
        decoded = set()
        for source in sources.values():
            path = checked(root, source["local_path"], source["sha256"])
            provider = providers[source["provider"]]
            if source.get("git_blob_sha"):
                if git_blob_sha(path.read_bytes()) != source["git_blob_sha"]:
                    raise ValueError("Pinned source Git blob mismatch")
                label = checked(root, source["label_local_path"], source["label_sha256"])
                if git_blob_sha(label.read_bytes()) != source["label_git_blob_sha"]:
                    raise ValueError("Pinned annotation blob mismatch")
            else:
                with zipfile.ZipFile(root / provider["archive"]) as archive:
                    if hashlib.sha256(archive.read(source["archive_entry"])).hexdigest() != source["sha256"]:
                        raise ValueError("Archive member provenance mismatch")
            image = cv2.imread(str(path))
            if image is None or image.shape[:2] != (source["height"], source["width"]):
                raise ValueError("Decoded source dimensions changed")
            pixel_hash = hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()
            if pixel_hash in old_pixels or source["sha256"] in old_files or duplicate_hits(image_feature(image), references):
                raise ValueError("New source overlaps prior dataset by exact/near-image screening")
            if pixel_hash in decoded:
                raise ValueError("Same new image counted under multiple source IDs")
            decoded.add(pixel_hash)
            for region in packet["regions"]:
                if region["source_id"] != source["id"]:
                    continue
                x1, y1, x2, y2 = region["roi"]
                encoded = cv2.imencode(".png", image[y1:y2, x1:x2])[1].tobytes()
                if hashlib.sha256(encoded).hexdigest() != region["patch_sha256"]:
                    raise ValueError("Reviewed context pixels changed")
                if export:
                    image_rel, label_rel = f'images/train/{region["id"]}.png', f'labels/train/{region["id"]}.txt'
                    for relative in (image_rel, label_rel):
                        destination = (export / relative).resolve()
                        if not destination.is_relative_to(export.resolve()):
                            raise ValueError("Foreign region ID path")
                        destination.parent.mkdir(parents=True, exist_ok=True)
                    (export / image_rel).write_bytes(encoded)
                    (export / label_rel).write_text(crop_labels(region), encoding="utf-8")
                    exported.append({"source_id": source["id"], "region_id": region["id"], "split": "train", "image": image_rel,
                                     "label": label_rel, "image_sha256": digest(export / image_rel), "label_sha256": digest(export / label_rel)})
    report = {"kind": "role_counterexample_audit_v3", "packet_sha256": digest(packet_path), "protected_manifest_sha256": digest(manifest_path),
              "sources": len(sources), "scene_groups": len({s["scene_family"] for s in sources.values()}), "reviewed_regions": len(seen),
              "primary_counts": {f"{role}/{color}": count for (role, color), count in counts.items()},
              "assets_verified": verify_assets, "prior_images_screened": len(manifest["files"]) if verify_assets else 0,
              "prior_duplicate_hits": 0 if verify_assets else None, "exported_regions": len(exported),
              "training_performed": False, "independently_validated": False, "full_frames_are_training_ready": False,
              "limitation": "Hash/thumbnail and visual scene checks do not prove independently verified disjoint matches; observations may repeat the same people."}
    if export:
        (export / "manifest.json").write_text(json.dumps({"names": NAMES, "audit": report, "files": exported}, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--verify-assets", action="store_true")
    parser.add_argument("--export", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = validate(root, checked(root, args.packet), args.verify_assets, args.export.resolve() if args.export else None)
    if args.report:
        destination = args.report.resolve()
        if not destination.is_relative_to(root) or destination.exists():
            raise ValueError("Report must be new and stay in workspace")
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
