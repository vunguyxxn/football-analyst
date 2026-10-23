"""Reproducible synthetic stress comparison and unlabeled Metrica coverage."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from backend.tactics.formation import spatial_shape
from backend.tactics.formation_templates import POLICY, template_shape
from backend.tactics.formation_aligned import POLICY as ALIGNED_POLICY, aligned_shape


def alignment_stress_fixture(fixture, config):
    result = deepcopy(fixture)
    result["label_source"] = "constructed_tilt_and_lateral_shift_stress"
    for case in result["cases"]:
        if case["expected_shape"] is None:
            continue
        xy = np.asarray(case["xy"], dtype=float)
        xy[:-1, 0] += config["physical_x_shear_per_y"] * (xy[:-1, 1] - 34)
        counts = list(map(int, case["expected_shape"].split("-")))
        offset = 0
        for count, shift in zip(counts, np.linspace(config["lateral_line_shift_start_m"],
                                                   config["lateral_line_shift_stop_m"], len(counts))):
            xy[offset:offset + count, 1] += shift
            offset += count
        case["xy"] = xy.tolist()
    return result


def synthetic_evaluation(fixture, *, include_aligned=False):
    recognizers = [("gap", spatial_shape), ("template", template_shape)]
    if include_aligned:
        recognizers.append(("aligned", aligned_shape))
    records = []
    for case in fixture["cases"]:
        for seed in fixture["seeds"]:
            for direction, x_scale, y_scale in ((1, 1., 1.), (-1, .8, .9), (1, 1.05, .8)):
                xy = np.asarray(case["xy"], dtype=float)
                # The last point is the goalkeeper in these constructed fixtures.
                xy = (xy - [52.5, 34]) * [direction * x_scale, y_scale] + [52.5, 34]
                xy += np.random.default_rng(seed).normal(0, fixture["noise_sigma_m"], xy.shape)
                points = {i + 1: point.tolist() for i, point in enumerate(xy[:-1])}
                points[11] = xy[-1].tolist()
                row = {"case_id": case["id"], "seed": seed, "direction": direction,
                       "x_scale": x_scale, "y_scale": y_scale, "expected_shape": case["expected_shape"]}
                for name, recognizer in recognizers:
                    result = recognizer(points, 11, direction)
                    row[name] = {"shape": result.get("shape"), "reason": result.get("reason")}
                records.append(row)
    summaries = {}
    for method, _ in recognizers:
        emitted = sum(r[method]["shape"] is not None for r in records)
        correct = sum(r[method]["shape"] is not None and r[method]["shape"] == r["expected_shape"] for r in records)
        confusion = Counter((r["expected_shape"] or "unknown", r[method]["shape"] or "unknown") for r in records)
        summaries[method] = {"total_cases": len(records), "emitted": emitted,
                             "abstained": len(records) - emitted, "correct_emitted": correct,
                             "selective_accuracy_synthetic": correct / emitted if emitted else None,
                             "known_shape_cases": sum(r["expected_shape"] is not None for r in records),
                             "false_emits_on_unknown_cases": sum(r["expected_shape"] is None and r[method]["shape"] is not None for r in records),
                             "confusion": [{"expected": a, "predicted": b, "count": n}
                                           for (a, b), n in sorted(confusion.items())]}
    return {"label_source": fixture["label_source"], "independent_real_ground_truth": False,
            "summaries": summaries, "cases": records}


def compare_metrica_reports(reports, *, include_aligned=False):
    recognizers = [("gap", spatial_shape), ("template", template_shape)]
    if include_aligned:
        recognizers.append(("aligned", aligned_shape))
    rows = []
    seen = set()
    for report in reports:
        if report.get("kind") != "offline_metrica_tactics_v1":
            raise ValueError("Expected Metrica tactics report")
        for team in report["teams"]:
            for window in team["formation_windows"]:
                key = (report["game"], report["period"], team["team"], window["start_s"], window["stop_s"])
                if key in seen:
                    raise ValueError("Duplicate evaluation window")
                seen.add(key)
                points = {p["track_id"]: p["median_position_m"] for p in window.get("players", [])}
                row = {"game": key[0], "period": key[1], "team": key[2], "start_s": key[3], "stop_s": key[4]}
                if not points:
                    for method, _ in recognizers:
                        row[method] = {"status": "unknown", "reason": window["reason"]}
                else:
                    for method, recognizer in recognizers:
                        row[method] = recognizer(points, team["goalkeeper_id"], team["attack_direction"])
                if points:
                    row["template_margin_sensitivity"] = {
                        str(margin): template_shape(points, team["goalkeeper_id"], team["attack_direction"],
                                                    minimum_margin=margin).get("shape")
                        for margin in (.04, .08, .12)}
                rows.append(row)
    return {"has_reference_labels": False, "total_windows": len(rows),
            "emitted": {m: sum(r[m]["status"] == "observed_shape" for r in rows) for m, _ in recognizers},
            "windows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-aligned", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if not output.is_relative_to(root) or any(not p.resolve().is_relative_to(root) for p in args.reports):
        parser.error("Paths must stay inside project")
    if output.exists():
        parser.error("Output already exists")
    fixture_path = root / "docs/fixtures/formation_template_cases.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    reports, sources = [], []
    for path in args.reports:
        payload = path.read_bytes()
        reports.append(json.loads(payload))
        sources.append({"path": path.resolve().relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(payload).hexdigest()})
    if not args.reports:
        path = root / "docs/fixtures/metrica_formation_windows.json"
        payload = path.read_bytes()
        reports = json.loads(payload)["reports"]
        sources.append({"path": path.relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(payload).hexdigest()})
    result = {"kind": "formation_comparison_v1", "template_policy": POLICY,
              "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
              "source_reports": sources, "synthetic": synthetic_evaluation(fixture, include_aligned=args.include_aligned),
              "metrica": compare_metrica_reports(reports, include_aligned=args.include_aligned)}
    if args.include_aligned:
        result["aligned_policy"] = ALIGNED_POLICY
        path = root / "docs/fixtures/formation_alignment_stress.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        result["alignment_stress_configuration"] = config
        result["alignment_stress_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        result["alignment_stress"] = synthetic_evaluation(alignment_stress_fixture(fixture, config), include_aligned=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"synthetic": result["synthetic"]["summaries"],
                      "metrica_emitted": result["metrica"]["emitted"]}))


if __name__ == "__main__":
    main()
