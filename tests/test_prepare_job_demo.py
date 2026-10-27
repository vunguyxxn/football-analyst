import json
from pathlib import Path

import pytest

from backend.cv import prepare_video_demo as demo


def test_demo_switch_verifies_source_preserves_previous_manifest_and_old_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "workspace_path", lambda path: Path(path).resolve())
    job_id = "a" * 32
    folder = tmp_path / "data/processed/video_jobs" / job_id
    folder.mkdir(parents=True)
    source = tmp_path / "Video Project 15.mp4"
    source.write_bytes(b"new demo source")
    (folder / "source.mp4").write_bytes(source.read_bytes())
    (folder / "chunk-0.json").write_text('{"frames": []}')
    status = {"status": "completed", "result": {"frames": 30, "fps": 30, "duration_s": 1, "chunks": 1}}
    (folder / "status.json").write_text(json.dumps(status))
    output = tmp_path / "demo"
    output.mkdir()
    (output / "manifest.json").write_text('{"version": 1}')
    (output / "tracking.jsonl").write_text("old pitch coordinates")
    manifest = demo.prepare_job(job_id, source, output, source.name)
    assert manifest["version"] == 2 and manifest["name"] == source.name
    assert (output / f"{job_id}.mp4").read_bytes() == source.read_bytes()
    assert (output / "tracking.jsonl").read_text() == "old pitch coordinates"
    assert len(list(output.glob("manifest-backup-*.json"))) == 1
    assert "tracking_sha256" not in manifest and "offset_seconds" not in manifest
    source.write_bytes(b"different source")
    with pytest.raises(ValueError, match="does not match"):
        demo.prepare_job(job_id, source, output, source.name)


def test_demo_cannot_reference_unfinished_job_or_invalid_id(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "workspace_path", lambda path: Path(path).resolve())
    with pytest.raises(ValueError):
        demo.prepare_job("../foreign", tmp_path / "x", tmp_path / "demo", "x")
    job_id = "b" * 32
    folder = tmp_path / "data/processed/video_jobs" / job_id
    folder.mkdir(parents=True)
    (folder / "status.json").write_text('{"status": "running"}')
    with pytest.raises(ValueError, match="completed"):
        demo.prepare_job(job_id, tmp_path / "x", tmp_path / "demo", "x")
