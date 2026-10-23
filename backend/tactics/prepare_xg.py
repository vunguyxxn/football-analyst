"""Prepare pinned StatsBomb shot CSV without changing the existing event cache."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pandas as pd
import requests

from backend.common.pitch import statsbomb_to_pitch
from backend.tactics.xg import FEATURES, OUTCOMES, shot_features

ROOT = Path(__file__).resolve().parents[2]


def workspace(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Paths must stay in project")
    return path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_blob(path, spec):
    data = path.read_bytes()
    if len(data) != spec["size"] or hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != spec["blob_sha1"]:
        raise ValueError(f"Pinned source hash mismatch: {path.name}")


def fetch_source(inventory, source):
    def fetch(spec):
        path = source / spec["path"]
        if not path.resolve().is_relative_to(source.resolve()):
            raise ValueError("Foreign source path")
        if path.exists():
            check_blob(path, spec)
            return
        url = f"https://raw.githubusercontent.com/{inventory['repo']}/{inventory['revision']}/{spec['path']}"
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=(15, 60))
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                partial = path.with_suffix(path.suffix + ".download")
                partial.write_bytes(response.content)
                check_blob(partial, spec)
                partial.replace(path)
                return
            except requests.RequestException:
                if attempt == 2:
                    raise
    with ThreadPoolExecutor(max_workers=6) as executor:
        for i, _ in enumerate(executor.map(fetch, inventory["files"]), 1):
            if i % 30 == 0:
                print(f"verified {i}/{len(inventory['files'])} files", flush=True)


def split_matches(matches, protocol):
    if len({m["match_id"] for m in matches}) != len(matches):
        raise ValueError("Duplicate match across competitions")
    dev, test = [], []
    for match in matches:
        key = [match["competition_id"], match["season_id"]]
        if key in protocol["development_competitions"]:
            dev.append(match)
        elif key in protocol["test_competitions"]:
            test.append(match)
        else:
            raise ValueError("Unspecified competition")
    if not dev or not test or max(m["match_date"] for m in dev) >= min(m["match_date"] for m in test):
        raise ValueError("Test must be a later, separate tournament")
    ordered = sorted(dev, key=lambda m: hashlib.sha256(f"{protocol['seed']}:{m['match_id']}".encode()).hexdigest())
    nval = max(1, round(len(dev) * protocol["validation_match_fraction"]))
    if nval >= len(dev):
        raise ValueError("Need training and validation matches")
    return {m["match_id"]: "val" if i < nval else "train" for i, m in enumerate(ordered)} | {m["match_id"]: "test" for m in test}


def extract_shots(events, match, split):
    rows, excluded = [], Counter()
    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        shot = event.get("shot", {})
        if event.get("period") not in (1, 2, 3, 4):
            excluded["non_playing_period"] += 1
            continue
        if shot.get("type", {}).get("name") == "Penalty":
            excluded["penalty"] += 1
            continue
        outcome = shot.get("outcome", {}).get("name")
        if outcome not in OUTCOMES:
            raise ValueError(f"Unknown shot outcome: {outcome}")
        try:
            features = shot_features(event)
        except (ValueError, TypeError):
            excluded["invalid_features"] += 1
            continue
        reference = shot.get("statsbomb_xg")
        if isinstance(reference, bool) or not isinstance(reference, (int, float)) or not 0 <= reference <= 1:
            excluded["missing_invalid_provider_xg"] += 1
            continue
        if not event.get("id"):
            raise ValueError("Shot must have an event ID")
        xm, ym = statsbomb_to_pitch(*event["location"][:2])
        rows.append({**match, "split": split, "event_id": event["id"], "target": int(outcome == "Goal"),
                     "statsbomb_xg": reference, "x_m": xm, "y_m": ym, **features})
    return rows, dict(excluded)


def prepare(output, download=False):
    output = workspace(output)
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads((ROOT / "docs/fixtures/xg_protocol_v1.json").read_text())
    inventory = json.loads((ROOT / "docs/fixtures/xg_source_inventory_v1.json").read_text())
    if (protocol["repo"], protocol["revision"]) != (inventory["repo"], inventory["revision"]):
        raise ValueError("Source/protocol differ")
    if protocol["features"] != list(FEATURES) or protocol["periods"] != [1, 2, 3, 4] or protocol["exclude_shot_types"] != ["Penalty"] or protocol["goal_width_m"] != 7.32:
        raise ValueError("Preparation differs from fixed protocol")
    source = ROOT / "data/raw/statsbomb_xg_v1"
    if download:
        fetch_source(inventory, source)
    for spec in inventory["files"]:
        check_blob(source / spec["path"], spec)
    matches = []
    for competition, season in protocol["development_competitions"] + protocol["test_competitions"]:
        for item in json.loads((source / f"data/matches/{competition}/{season}.json").read_text(encoding="utf-8")):
            matches.append({"match_id": item["match_id"], "match_date": item["match_date"],
                            "competition_id": competition, "season_id": season})
    assignments = split_matches(matches, protocol)
    rows, excluded = [], Counter()
    for match in sorted(matches, key=lambda m: m["match_id"]):
        events = json.loads((source / f"data/events/{match['match_id']}.json").read_text(encoding="utf-8"))
        shots, dropped = extract_shots(events, match, assignments[match["match_id"]])
        rows.extend(shots)
        excluded.update(dropped)
    frame = pd.DataFrame(rows)
    if frame.event_id.duplicated().any() or set(frame.split) != {"train", "val", "test"}:
        raise ValueError("Duplicate shots or empty split")
    output.mkdir(parents=True)
    frame.to_csv(output / "shots.csv", index=False, encoding="utf-8")
    manifest = {"kind": "statsbomb_xg_dataset_v1", "protocol": protocol, "shots_sha256": digest(output / "shots.csv"),
                "inventory_sha256": digest(ROOT / "docs/fixtures/xg_source_inventory_v1.json"),
                "matches": [{**m, "split": assignments[m["match_id"]]} for m in matches],
                "counts": {s: {"matches": int((pd.Series(assignments).eq(s)).sum()), "shots": len(g), "goals": int(g.target.sum())}
                           for s, g in frame.groupby("split")}, "excluded": dict(excluded)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"counts": manifest["counts"], "excluded": manifest["excluded"]}), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    prepare(args.output, args.download)
