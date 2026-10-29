"""Integration: a successful camera alone cannot publish unchecked coordinates."""
import hashlib
import json

import numpy as np
import pytest

from backend.cv import project_uploaded_job as module


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    job = tmp_path / "job"
    job.mkdir()
    source = b"synthetic source identity"
    (job / "source.mp4").write_bytes(source)
    (job / "status.json").write_text(json.dumps({"status": "completed", "result": {
        "width": 105, "height": 68, "frames": 24, "fps": 10, "chunks": 1}}))
    records = [{"frame": i, "boxes": [{"id": 1, "group": "A", "xyxy": [18, 5, 22, 20]}]}
               for i in range(24)]
    (job / "chunk-0.json").write_text(json.dumps({"frames": records}))
    identity = {"source_sha256": hashlib.sha256(source).hexdigest(), "image_size": [105, 68]}
    points = [[0, 0], [104, 0], [104, 67], [0, 67]]
    controls = tmp_path / "controls.json"
    controls.write_text(json.dumps({**identity, "pitch_m": [105, 68], "anchors": [
        {"frame": start, "end_frame": start + 12, "image_points": points, "pitch_points": points}
        for start in (0, 12)]}))
    checks = tmp_path / "checks.json"
    checks.write_text(json.dumps({**identity, "max_error_m": 1, "max_gap_frames": 5,
        "checkpoints": [{"frame": i, "image_points": [[20, 20], [40, 40]],
                         "pitch_points": [[20 + shift, 20], [40 + shift, 40]]}
                        for i, shift in [(1, 0), (13, 0), (18, 2)]]}))

    class Capture:
        def read(self):
            return True, np.zeros((68, 105, 3), dtype=np.uint8)

        def release(self):
            pass

    class Camera:
        matrix = previous = mask = None
        failed = False

        def update(self, frame, boxes, anchor=None):
            if anchor is not None:
                self.matrix, self.failed = anchor.copy(), False
            if self.failed:
                return {"status": "lost"}
            return {"status": "tracked"}

    monkeypatch.setattr(module.cv2, "VideoCapture", lambda _: Capture())
    monkeypatch.setattr(module, "CameraMotion", Camera)
    return job, controls, checks


def test_pending_expired_drift_and_reanchor_gate_actual_output(tmp_path, monkeypatch):
    job, controls, checks = fixture(tmp_path, monkeypatch)
    output = tmp_path / "output"
    report = module.project_job(job, controls, output, checks)
    rows = [json.loads(line) for line in (output / "tracking.jsonl").read_text().splitlines()]
    assert [row["frame"] for row in rows] == [3, 4, 5, 6, 15, 16, 17]
    # Odd input width exercises full-size vs half-size landmark coordinate handling.
    assert all(row["x_m"] == pytest.approx(20) and row["y_m"] == pytest.approx(20) for row in rows)
    assert report["calibrated_intervals"] == [
        {"start_s": .1, "end_s": .7}, {"start_s": 1.3, "end_s": 1.8}]
    results = report["landmark_checks"]["results"]
    assert [(item["frame"], item.get("reason")) for item in results] == [
        (1, None), (7, "landmark_check_expired"), (13, None), (18, "landmark_drift_exceeded")]
    assert report["landmark_checks"]["independently_validated"] is False
    assert {player["segment"] for player in report["players"]} == {0, 1}


def test_mismatched_check_source_rejected_before_output(tmp_path, monkeypatch):
    job, controls, checks = fixture(tmp_path, monkeypatch)
    payload = json.loads(checks.read_text())
    payload["source_sha256"] = "different clip"
    checks.write_text(json.dumps(payload))
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="mismatch"):
        module.project_job(job, controls, output, checks)
    assert not output.exists()
