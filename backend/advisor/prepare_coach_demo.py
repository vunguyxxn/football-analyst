"""Copy the frozen advisor example after checking its source/model hashes."""
import json
from pathlib import Path
import shutil

from backend.cv.prepare_video_review import digest

ROOT = Path(__file__).resolve().parents[2]


def prepare():
    output = ROOT / "frontend/public/coach-demo"
    if output.exists():
        raise FileExistsError("Coach demo exists; no files were overwritten")
    report_path = ROOT / "data/processed/advisor_8650_v1_final/advisor.json"
    frozen = json.loads((ROOT / "docs/fixtures/advisor_result_v1.json").read_text(encoding="utf-8"))
    if digest(report_path) != frozen["report_sha256"]:
        raise ValueError("Advisor differs from the frozen, audited report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model = ROOT / "data/processed/xg_model_v1"
    if digest(model / "model.json") != report["model_audit"]["model_sha256"] or digest(model / "model_metadata.json") != report["model_audit"]["model_metadata_sha256"]:
        raise ValueError("Source model/metadata differ")
    events = ROOT / f"data/raw/statsbomb_xg_v1/data/events/{report['match_id']}.json"
    if digest(events) != report["provenance"]["events_sha256"]:
        raise ValueError("Source events differ from the report")
    output.mkdir(parents=True)
    shutil.copyfile(report_path, output / "advisor.json")
    manifest = {"report_sha256": digest(report_path), "model_sha256": report["model_audit"]["model_sha256"],
                "match_id": report["match_id"], "shots": len(report["shots"]),
                "cards": sum(len(t["recommendations"]) for t in report["teams"]), "source_and_model_verified": True}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    prepare()
