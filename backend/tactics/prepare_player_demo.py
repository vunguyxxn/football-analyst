"""Prepare local player-viewer examples, verifying reports against sources."""
import json
from pathlib import Path
import shutil

import pandas as pd

from backend.cv.prepare_video_review import digest
from backend.tactics.metrica_report import load_tracking, player_profile
from backend.tactics.statsbomb_profiles import build_profiles

ROOT = Path(__file__).resolve().parents[2]


def prepare():
    output = ROOT / "frontend/public/player-demo"
    if output.exists():
        raise FileExistsError("Player demo already exists; existing files are not overwritten")
    source = ROOT / "data/processed/formation_v1"
    stats_path = source / "statsbomb_8650_player_profiles_v1.json"
    tracking_path = source / "game1_tactics_profiles.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    csv = (ROOT / stats["source_path"]).resolve()
    if not csv.is_relative_to(ROOT) or digest(csv) != stats["source_sha256"]:
        raise ValueError("StatsBomb cache source mismatch")
    rebuilt = build_profiles(pd.read_csv(csv), stats["match_id"])
    if stats["players"] != rebuilt["players"]:
        raise ValueError("StatsBomb profiles differ from recomputed source events")
    tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "docs/fixtures/metrica_benchmark.json").read_text(encoding="utf-8"))
    expected = {f["filename"]: f["sha256"] for f in manifest["files"]}
    for item in tracking["sources"]:
        raw = (ROOT / item["path"]).resolve()
        if not raw.is_relative_to(ROOT) or digest(raw) != item["sha256"] or item["sha256"] != expected[raw.name]:
            raise ValueError("Metrica source hash mismatch")
        trajectories, _ = load_tracking(raw, tracking["game"], item["team"], tracking["start_s"], tracking["stop_s"], tracking["period"])
        team = next(t for t in tracking["teams"] if t["team"] == item["team"])
        profiles = [player_profile(t, tracking["start_s"], tracking["stop_s"], team["goalkeeper_id"])
                    for t in sorted(trajectories, key=lambda t: t.track_id)]
        if profiles != team["players"]:
            raise ValueError("Metrica profiles differ from recomputed source tracking")
    output.mkdir(parents=True)
    shutil.copyfile(stats_path, output / "statsbomb.json")
    shutil.copyfile(tracking_path, output / "metrica.json")
    audit = {"statsbomb": {"players": len(stats["players"]), "sha256": digest(stats_path)},
             "metrica": {"players": sum(len(t["players"]) for t in tracking["teams"]), "sha256": digest(tracking_path)},
             "recomputed_profiles_match": True}
    (output / "manifest.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit))


if __name__ == "__main__":
    prepare()
