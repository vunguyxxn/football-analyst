"""Research-only ball continuity and possible handovers; no confirmed event totals."""
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


class BallContinuity:
    def __init__(self, width, height, fps):
        self.diagonal = math.hypot(width, height)
        self.fps = fps
        self.history = deque(maxlen=5)
        self.last_frame = -1
        self.segment = 0

    def reset(self):
        self.history.clear()
        self.segment += 1

    def update(self, frame, candidates, *, cut=False):
        if frame <= self.last_frame:
            raise ValueError("Frames must increase")
        self.last_frame = frame
        if cut or (self.history and frame - self.history[-1][0] > max(1, round(self.fps * .15))):
            self.reset()
        usable = []
        for item in candidates:
            x1, y1, x2, y2 = item["xyxy"]
            if not np.isfinite([x1, y1, x2, y2, item["score"]]).all():
                continue
            if min(x2 - x1, y2 - y1) < 2 or not .5 <= (x2 - x1) / (y2 - y1) <= 2 or max(x2 - x1, y2 - y1) > self.diagonal * .025:
                continue
            center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
            if self.history:
                last_frame, last = self.history[-1]
                dt = (frame - last_frame) / self.fps
                velocity = np.zeros(2)
                if len(self.history) >= 2:
                    first_frame, first = self.history[-2]
                    velocity = (last - first) * self.fps / (last_frame - first_frame)
                prediction = last + velocity * dt
                error = np.linalg.norm(center - prediction)
                radius = self.diagonal * (.007 + .35 * dt)
                if error > radius:
                    continue
                score = item["score"] - .4 * error / radius
            else:
                if item["score"] < .25:
                    continue
                score = item["score"]
            usable.append((score, item, center))
        usable.sort(key=lambda value: -value[0])
        if not usable or (len(usable) > 1 and usable[0][0] - usable[1][0] < .08):
            return None
        _, selected, center = usable[0]
        gap_frames = frame - self.history[-1][0] - 1 if self.history else 0
        self.history.append((frame, center))
        if len(self.history) < 3:
            return None
        return {"center_px": center.tolist(), "xyxy": selected["xyxy"], "score": selected["score"], "segment": self.segment,
                "gap_frames": gap_frames}


def contact_candidate(ball, people):
    if ball is None:
        return None
    x, y = ball["center_px"]
    ranked = []
    for person in people:
        left, top, right, bottom = person["xyxy"]
        height = bottom - top
        if height < 12:
            continue
        distance = math.hypot(x - (left + right) / 2, y - bottom) / height
        if distance <= .65:
            ranked.append((distance, person))
    ranked.sort(key=lambda item: item[0])
    if not ranked or (len(ranked) > 1 and ranked[1][0] - ranked[0][0] < .25):
        return None
    person = ranked[0][1]
    return {"id": person["id"], "group": person["group"], "distance_in_body_heights": ranked[0][0]}


class HandoverCandidates:
    def __init__(self, fps):
        self.fps = fps
        self.votes = deque(maxlen=max(3, round(.15 * fps)))
        self.previous = None
        self.events = []
        self.segment = None
        self.free_frames = 0
        self.flight_observed = 0
        self.recipient_ids = set()
        self.last_ball_frame = None
        self.missing_frames = 0

    def update(self, frame, ball, contact, people):
        if ball is None and self.last_ball_frame is not None and frame - self.last_ball_frame <= max(1, round(.1 * self.fps)):
            self.votes.clear()
            self.missing_frames += 1
            return
        if ball is None or (self.segment is not None and ball["segment"] != self.segment):
            self.votes.clear()
            self.previous = None
            self.free_frames = self.flight_observed = 0
            self.recipient_ids.clear()
            self.segment = None if ball is None else ball["segment"]
            self.last_ball_frame = None if ball is None else frame
            self.missing_frames = 0
            return
        self.segment = ball["segment"]
        self.last_ball_frame = frame
        if contact is None:
            self.votes.clear()
            if self.previous:
                self.free_frames += 1
                self.flight_observed += 1
            return
        self.votes.append(contact["id"])
        if len(self.votes) < self.votes.maxlen or len(set(self.votes)) != 1:
            return
        current = {**contact, "frame": frame, "center_px": ball["center_px"]}
        if self.previous and current["id"] != self.previous["id"]:
            elapsed = (frame - self.previous["frame"]) / self.fps
            moved = math.dist(current["center_px"], self.previous["center_px"])
            if (.15 <= elapsed <= 3 and self.free_frames >= 2 and current["id"] in self.recipient_ids
                    and current["group"] == self.previous["group"] and current["group"] in ("A", "B") and moved >= 30
                    and self.missing_frames / max(1, frame - self.previous["frame"]) <= .2):
                self.events.append({"kind": "possible_pass", "status": "unverified", "start_s": self.previous["frame"] / self.fps,
                                    "end_s": frame / self.fps, "from_id": self.previous["id"], "to_id": current["id"],
                                    "group": current["group"], "missing_ball_frames": self.missing_frames,
                                    "evidence": "observed ball with bounded short gaps, sustained near-foot association, same color group; NOT confirmed contact or pass"})
        if self.previous is None or current["id"] != self.previous["id"]:
            self.recipient_ids = {person["id"] for person in people}
        self.previous = current
        self.free_frames = self.flight_observed = 0
        self.missing_frames = 0


def field_region(frame):
    """Coarse green-region rejection only; never used as metric calibration."""
    import cv2
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (30, 40, 30), (90, 255, 255))
    # Screen recordings can contain white controls over green outside the pitch.
    # A grass hull alone includes these. Require a long near touchline and clip
    # below it; this is an experimental image-space filter, not homography.
    small = cv2.resize(hsv, (960, round(960 * frame.shape[0] / frame.shape[1])))
    white = cv2.inRange(small, (0, 0, 150), (180, 110, 255))
    white[:round(white.shape[0] * .55)] = 0
    lines = cv2.HoughLinesP(white, 1, np.pi / 720, 40, minLineLength=white.shape[1] * .35, maxLineGap=30)
    eligible = []
    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            if abs(x2 - x1) < 1 or abs(y2 - y1) > .3 * abs(x2 - x1):
                continue
            slope = (y2 - y1) / (x2 - x1)
            intercept = y1 - slope * x1
            middle_y = slope * white.shape[1] / 2 + intercept
            if .55 * white.shape[0] < middle_y < .995 * white.shape[0]:
                eligible.append((abs(x2 - x1) / (1 + 3 * abs(slope)), slope, intercept))
    if not eligible:
        return None
    _, slope, intercept = max(eligible)
    yy, xx = np.ogrid[:frame.shape[0], :frame.shape[1]]
    cutoff = slope * xx + intercept * frame.shape[1] / 960
    mask[yy > cutoff + 4] = 0
    mask = cv2.erode(mask, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < frame.shape[0] * frame.shape[1] * .1:
        return None
    return cv2.convexHull(largest)


def run(job_folder, output, replay=None):
    import cv2
    from backend.cv.ball_probe import detect_candidates
    for path in (job_folder, output):
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError("Paths must remain in workspace")
    if output.exists():
        raise FileExistsError(output)
    status = json.loads((job_folder / "status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Person job must be completed")
    source = next(job_folder.glob("source.*"))
    result = status["result"]
    os.environ["YOLO_CONFIG_DIR"] = str(ROOT / ".tmp/ultralytics")
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    replay_stream = None
    if replay is not None:
        replay = replay.resolve()
        if not replay.is_relative_to(ROOT):
            raise ValueError("Replay path must remain in workspace")
        previous_report = json.loads((replay / "report.json").read_text(encoding="utf-8"))
        if previous_report["source_sha256"] != source_hash or previous_report["frames"] != result["frames"]:
            raise ValueError("Replay source differs")
        replay_stream = (replay / "ball.jsonl").open(encoding="utf-8")
    else:
        from ultralytics import YOLO
        import torch
        weights = ROOT / "data/processed/ball_finetune_v1/training/weights/best.pt"
        model = YOLO(str(weights))
        device = "0" if torch.cuda.is_available() else "cpu"
    output.mkdir(parents=True)
    tracker = BallContinuity(result["width"], result["height"], result["fps"])
    handovers = HandoverCandidates(result["fps"])
    capture = cv2.VideoCapture(str(source))
    observed = contacts = cuts = 0
    previous_thumbnail = None
    frame_index = 0
    try:
        with (output / "ball.jsonl").open("w", encoding="utf-8") as stream:
            for chunk_index in range(result["chunks"]):
                chunk = json.loads((job_folder / f"chunk-{chunk_index}.json").read_text(encoding="utf-8"))
                for row in chunk["frames"]:
                    ok, frame = capture.read()
                    if not ok or row["frame"] != frame_index:
                        raise ValueError("Video/person records differ")
                    thumbnail = cv2.resize(frame, (96, 54)).astype(float) / 255
                    cut = previous_thumbnail is not None and float(np.mean(np.abs(thumbnail - previous_thumbnail))) > .2
                    previous_thumbnail = thumbnail
                    cuts += cut
                    if replay_stream is not None:
                        cached = json.loads(next(replay_stream))
                        if cached["frame"] != frame_index:
                            raise ValueError("Replay frame differs")
                        candidates = cached["raw_candidates"]
                    else:
                        candidates = detect_candidates(model, frame, device=device, tiled=False, confidence=.1)
                    raw_candidates = candidates
                    region = field_region(frame)
                    candidates = [] if region is None else [item for item in candidates if cv2.pointPolygonTest(region, ((item["xyxy"][0] + item["xyxy"][2]) / 2, (item["xyxy"][1] + item["xyxy"][3]) / 2), False) >= 0]
                    ball = tracker.update(frame_index, candidates, cut=cut)
                    contact = contact_candidate(ball, row["boxes"])
                    observed += ball is not None
                    contacts += contact is not None
                    handovers.update(frame_index, ball, contact, row["boxes"])
                    stream.write(json.dumps({"frame": frame_index, "time_s": row["time_s"], "raw_candidates": raw_candidates,
                                             "field_region_available": region is not None, "ball": ball, "contact_candidate": contact}) + "\n")
                    frame_index += 1
                print(json.dumps({"frames": frame_index, "ball_observed": observed, "near_foot_candidates": contacts}), flush=True)
    finally:
        capture.release()
        if replay_stream:
            replay_stream.close()
    if frame_index != result["frames"]:
        raise ValueError("Decoded frame count differs")
    report = {"kind": "ball_sequence_research_v1", "source_sha256": source_hash, "person_job_id": job_folder.name, "frames": frame_index,
              "ball_observed_frames": observed, "near_foot_candidate_frames": contacts, "cut_resets": cuts,
              "possible_passes": handovers.events, "confirmed_passes": None, "shots": None,
              "warning": "Experimental pixel-space ball continuity/near-foot associations. No independent ball/contact/event labels; do not display as confirmed football totals."}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_folder", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.job_folder, args.output, args.replay), ensure_ascii=False))
