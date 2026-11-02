"""Offline reference check of method cards through normalization and CSV reload.

Run: python -m backend.tactics.verify_event_metrics
No download, model loading or mutation of the event cache.
"""
from __future__ import annotations

import hashlib
from io import StringIO
import json
from pathlib import Path

import pandas as pd

from backend.tactics.event_metrics import compute_event_metrics
from backend.tactics.loader import normalize_events

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "docs/fixtures/event_metrics_reference_v1.json"


def reference_frame(events: list[dict], match_id: int) -> pd.DataFrame:
    """Flatten the pinned raw StatsBomb JSON fields needed by these methods.

    The source specification defines absent optional pass fields as absent,
    unlike an arbitrary CSV missing a whole column. Keep every column here.
    """
    records = []
    for event in events:
        detail = event.get("pass", {})
        records.append({
            "type": event.get("type"), "team": event.get("team"),
            "period": event.get("period"), "location": event.get("location"),
            "pass_outcome": detail.get("outcome"), "pass_type": detail.get("type"),
            "pass_cross": detail.get("cross"), "pass_body_part": detail.get("body_part"),
            "duel_type": event.get("duel", {}).get("type"),
            "shot_statsbomb_xg": event.get("shot", {}).get("statsbomb_xg"),
        })
    return normalize_events(pd.DataFrame(records), match_id)


def verify_reference() -> dict:
    spec = json.loads(REFERENCE.read_text(encoding="utf-8"))
    source = (ROOT / spec["local_events"]).resolve()
    if not source.is_relative_to(ROOT):
        raise ValueError("Reference source must stay in project")
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec["events_sha256"]:
        raise ValueError("Reference event SHA-256 does not match the pinned fixture")
    frame = reference_frame(json.loads(data), spec["match_id"])
    reloaded = pd.read_csv(StringIO(frame.to_csv(index=False)))
    results = {}
    for team, expected in spec["expected"].items():
        before = compute_event_metrics(frame, team)
        after = compute_event_metrics(reloaded, team)
        if before != after:
            raise ValueError(f"CSV round-trip changed metrics for {team}")
        observed = {metric.key: metric.value for metric in after.metrics}
        for key, value in expected.items():
            actual = observed.get(key)
            if not isinstance(actual, float) or abs(actual - value) > spec["tolerance"]:
                raise ValueError(f"Reference mismatch: {team}/{key}: {actual} != {value}")
        results[team] = observed
    return {"match_id": spec["match_id"], "events_sha256": digest,
            "data_revision": spec["data_revision"], "reference_revision": spec["reference_revision"],
            "csv_round_trip": True, "results": results}


if __name__ == "__main__":
    print(json.dumps(verify_reference(), ensure_ascii=False, indent=2))
