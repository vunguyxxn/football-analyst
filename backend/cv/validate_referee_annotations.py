"""Audit ROI-scoped referee annotations; never turn unlabelled frames into negatives."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from backend.cv.evaluate_role_detector import checked, digest


def box_inside(box, boundary):
    if len(box) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box):
        raise ValueError("Nonfinite/invalid annotation box")
    x1, y1, x2, y2 = box
    if not (boundary[0] <= x1 < x2 <= boundary[2] and boundary[1] <= y1 < y2 <= boundary[3]):
        raise ValueError("Annotation box outside reviewed bounds")


def known_frames(root):
    known = set()
    folder = root / "docs/fixtures"
    local = folder / "local_role_annotations_v1.json"
    if local.exists():
        for frame in json.loads(local.read_text(encoding="utf-8"))["frames"]:
            known.add((frame["source_sha256"], frame["frame"]))
    context = folder / "clip_f51735_context_review_v1.json"
    if context.exists():
        data = json.loads(context.read_text(encoding="utf-8"))
        known.update((data["source_sha256"], frame) for frame in data["frames"])
    crossclip = folder / "upload_crossclip_visual_labels_v1.json"
    if crossclip.exists():
        for clip in json.loads(crossclip.read_text(encoding="utf-8"))["clips"]:
            known.update((clip["source_sha256"], frame["frame"]) for frame in clip["frames"])
    return known


def validate(root, packet_path, verify_assets=False):
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet["kind"] != "referee_annotation_packet_v2" or packet["independently_validated"] is not False:
        raise ValueError("Unsupported packet or unsupported independent-validation claim")
    if packet["training_performed"] is not False or packet["runtime_changed"] is not False:
        raise ValueError("Annotation packet must not claim training/runtime changes")
    protocol_path = checked(root, packet["base_protocol"], packet["base_protocol_sha256"])
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    original_labels = json.loads(checked(root, protocol["local_annotations"], protocol["local_annotations_sha256"]).read_text(encoding="utf-8"))
    locked_videos = {Path(frame["source"]).name: frame["source_sha256"] for frame in original_labels["frames"]}
    sources = {source["id"]: source for source in packet["sources"]}
    if len(sources) != len(packet["sources"]):
        raise ValueError("Duplicate source IDs")
    old_frames = known_frames(root)
    for source in sources.values():
        if not re.fullmatch(r"[0-9a-f]{64}", source["source_sha256"]):
            raise ValueError("Missing source hash")
        if source["type"] == "video_frame":
            family = protocol["local_families"][Path(source["source"]).name]
            if source["source_sha256"] != locked_videos[Path(source["source"]).name]:
                raise ValueError("Video hash differs from locked source family")
            frame = source["frame"]
            if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0:
                raise ValueError("Invalid frame index")
            if (source["source_sha256"], frame) in old_frames:
                raise ValueError("Previously labelled frame cannot count as new")
        elif source["type"] == "image":
            family = protocol["prefix_families"][Path(source["source"]).name.split("_")[0]]
        else:
            raise ValueError("Unsupported source type")
        if source["family"] != family or source["split"] != "train" or protocol["family_splits"][family] != "train":
            raise ValueError("Protected validation/test source or mismatched family")
        if any(isinstance(source[key], bool) or not isinstance(source[key], int) or source[key] <= 0 for key in ("width", "height")):
            raise ValueError("Invalid image dimensions")
    identifiers, primary_keys, admitted_objects = set(), set(), set()
    counts, colors, poses = Counter(), Counter(), Counter()
    small, occluded, clipped = 0, 0, 0
    for region in packet["regions"]:
        source = sources[region["source_id"]]
        if region["id"] in identifiers or region["review_status"] != "agent_reviewed":
            raise ValueError("Duplicate region or unreviewed label")
        identifiers.add(region["id"])
        key = (source["id"], region["subject_id"])
        if key in primary_keys:
            raise ValueError("Duplicate primary observation")
        primary_keys.add(key)
        if region["coverage"] != "visible match targets inside ROI only; outside ROI unlabelled":
            raise ValueError("ROI-only scope required")
        box_inside(region["roi"], [0, 0, source["width"], source["height"]])
        if any(isinstance(v, bool) or not isinstance(v, int) for v in region["roi"]):
            raise ValueError("ROI must use integer pixels")
        if region["origin"] != ("new_local_frame" if source["type"] == "video_frame" else "reviewed_existing_source"):
            raise ValueError("Existing annotation cannot be counted as new")
        object_ids = set()
        for obj in region["objects"]:
            if obj["id"] in object_ids or obj["role"] not in {"player", "goalkeeper", "referee"}:
                raise ValueError("Duplicate object or invalid role")
            object_ids.add(obj["id"])
            admitted_objects.add((source["id"], obj["id"]))
            box_inside(obj["xyxy"], region["roi"])
        kind = region["kind"]
        if kind == "staff_background":
            if region["objects"]:
                raise ValueError("Background ROI contains labelled targets")
        elif kind in {"referee", "player_hard_negative"}:
            subject = next((obj for obj in region["objects"] if obj["id"] == region["subject_id"]), None)
            if subject is None or subject["role"] != ("referee" if kind == "referee" else "player"):
                raise ValueError("Primary role differs from reviewed subject")
            if kind == "referee":
                attrs = region["attributes"]
                if attrs["shirt_color"] not in {"light_blue", "yellow", "red", "black"} or attrs["pose"] not in {"front", "side", "back", "uncertain"} or attrs["occlusion"] not in {"none_visible", "partial"}:
                    raise ValueError("Unsupported visual attribute")
                height = (subject["xyxy"][3]-subject["xyxy"][1])*640/max(source["width"], source["height"])
                if abs(height-attrs["height_at_imgsz640"]) > .02:
                    raise ValueError("Small-object attribute inconsistent with box")
                small += height < 24
                occluded += attrs["occlusion"] == "partial"
                clipped += attrs["body_clipped_by_image"] is True
                colors[attrs["shirt_color"]] += 1
                poses[attrs["pose"]] += 1
        else:
            raise ValueError("Unknown reviewed region kind")
        counts[(region["origin"], kind)] += 1
    for item in packet["quarantine"]:
        source = sources[item["source_id"]]
        subject = item.get("subject_id", str(item.get("source_line")))
        if (source["id"], subject) in primary_keys or (source["id"], subject) in admitted_objects or not item["reason"]:
            raise ValueError("Quarantined observation admitted to labels")
        box_inside(item["xyxy"], [0, 0, source["width"], source["height"]])
    if verify_assets:
        import cv2
        verified_hashes = {}
        for source in sources.values():
            path = checked(root, source["source"])
            if path not in verified_hashes:
                verified_hashes[path] = digest(path)
            if verified_hashes[path] != source["source_sha256"]:
                raise ValueError("Source bytes changed")
            if source["type"] == "video_frame":
                cap = cv2.VideoCapture(str(path))
                try:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, source["frame"])
                    ok, image = cap.read()
                    if not ok:
                        raise ValueError("Cannot decode reviewed frame")
                finally:
                    cap.release()
                if hashlib.sha256(cv2.imencode(".png", image)[1].tobytes()).hexdigest() != source["raw_image_sha256"]:
                    raise ValueError("Reviewed frame hash changed")
            else:
                image = cv2.imread(str(path))
                checked(root / "data/raw/football_detection_source_v1", source["label_source"], source["label_source_sha256"])
            if image is None or image.shape[:2] != (source["height"], source["width"]):
                raise ValueError("Decoded image dimensions changed")
            for region in packet["regions"]:
                if region["source_id"] != source["id"]:
                    continue
                x1, y1, x2, y2 = region["roi"]
                encoded = cv2.imencode(".png", image[y1:y2, x1:x2])[1].tobytes()
                if hashlib.sha256(encoded).hexdigest() != region["patch_sha256"]:
                    raise ValueError("Reviewed ROI pixels changed")
    return {"kind": "referee_annotation_audit_v2", "packet_sha256": digest(packet_path), "assets_verified": verify_assets,
            "sources": len(sources), "new_local_frames": sum(s["type"] == "video_frame" for s in sources.values()),
            "new_local_referees": counts[("new_local_frame", "referee")], "reviewed_existing_referees": counts[("reviewed_existing_source", "referee")],
            "player_hard_negative_regions": counts[("new_local_frame", "player_hard_negative")], "staff_background_regions": counts[("new_local_frame", "staff_background")],
            "regions": len(identifiers), "quarantined": len(packet["quarantine"]), "referee_shirt_colors": dict(colors), "referee_poses": dict(poses),
            "referees_under_24px_at_imgsz640": small, "partial_occlusions": occluded, "image_clipped_referees": clipped,
            "training_performed": False, "independently_validated": False, "full_frames_are_training_ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--verify-assets", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    report = validate(root, checked(root, args.packet), args.verify_assets)
    if args.report:
        destination = args.report.resolve()
        if not destination.is_relative_to(root) or destination.exists():
            raise ValueError("Report must be a new file inside workspace")
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
