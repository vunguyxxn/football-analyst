"""Re-filter a completed cached job into a NEW job, preserving original artifacts/IDs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
from uuid import uuid4

import cv2

from backend.cv.pitch_boundary import pitch_region, inside_pitch

ROOT = Path(__file__).resolve().parents[2]


def filter_job(source_job, output):
    source_job, output = source_job.resolve(), output.resolve()
    if not all(path.is_relative_to(ROOT) for path in (source_job, output)) or output.exists():
        raise ValueError("Use workspace paths and a new output job")
    status = json.loads((source_job / "status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Source job must be completed")
    source = next(source_job.glob("source.*"))
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = dict(status["result"])
    if result.get("source_sha256", digest) != digest:
        raise ValueError("Source hash differs")
    output.mkdir(parents=True)
    capture = cv2.VideoCapture(str(source))
    groups, ids = Counter({"A": 0, "B": 0, "unknown": 0}), set()
    count = covered = removed = observations = 0
    try:
        for index in range(result["chunks"]):
            chunk = json.loads((source_job / f"chunk-{index}.json").read_text(encoding="utf-8"))
            for record in chunk["frames"]:
                ok, image = capture.read()
                if not ok or record["frame"] != count or image.shape[:2] != (result["height"], result["width"]):
                    raise ValueError("Video and cached detections differ")
                region = pitch_region(image)
                covered += region is not None
                kept = [box for box in record["boxes"] if inside_pitch(region, box["xyxy"])]
                removed += len(record["boxes"]) - len(kept)
                record["boxes"] = kept
                record["pitch_boundary"] = region.round(2).tolist() if region is not None else None
                for box in kept:
                    ids.add(box["id"])
                    groups[box["group"]] += 1
                observations += len(kept)
                count += 1
            (output / f"chunk-{index}.json").write_text(json.dumps(chunk), encoding="utf-8")
            print(json.dumps({"frames": count, "boundary_frames": covered, "removed": removed}), flush=True)
    finally:
        capture.release()
    if count != result["frames"]:
        raise ValueError("Frame count differs")
    shutil.copyfile(source, output / source.name)
    result.update(source_sha256=digest, track_ids=len(ids), observations=observations, group_observations=dict(groups),
                  boundary_filter={"method": "white_touchlines_grass_v1", "frames_with_boundary": covered,
                                   "excluded_observations": removed, "missing_boundary_policy": "no_tracking",
                                   "derived_from_job": source_job.name, "ids_preserved": True})
    result["limitations"] = [note for note in result.get("limitations", []) if not note.startswith("Chưa hiệu chỉnh")]
    result["limitations"] += ["Chỉ giữ điểm chân trong vùng biên trắng ước lượng; frame không rõ biên bị bỏ. Có thể bỏ sót khi che khuất hoặc góc quay cận.",
                              "Lọc biên ảnh không tạo tọa độ mét; heatmap/vận động chỉ thuộc đoạn hiệu chỉnh riêng."]
    payload = {**status, "id": output.name, "result": result}
    (output / "status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_job", type=Path)
    args = parser.parse_args()
    output = ROOT / "data/processed/video_jobs" / uuid4().hex
    payload = filter_job(args.source_job, output)
    print(json.dumps({"job_id": payload["id"], "boundary_filter": payload["result"]["boundary_filter"]}))
