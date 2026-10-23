"""Traceable, post-match shot-review suggestions from xG and Tree SHAP."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.tactics.pass_network import _short_names
from backend.tactics.prepare_xg import ROOT, check_blob, digest, split_matches, workspace
from backend.tactics.xg import FEATURES, feature_matrix, shot_features

GEOMETRY = ("distance_m", "angle_rad", "lateral_m")
FEATURE_LABELS = {"distance_m": "Khoảng cách tới cầu môn (m)", "angle_rad": "Góc mở cầu môn (rad)",
                  "lateral_m": "Độ lệch ngang (m)", "is_header": "Đánh đầu (0/1)",
                  "is_other_body": "Bộ phận khác đầu/chân (0/1)", "is_free_kick": "Sút phạt trực tiếp (0/1)",
                  "first_time": "First time (0/1)", "under_pressure": "Dưới áp lực (0/1)"}


def collect_shots(events):
    teams, rows, excluded, seen = {}, [], Counter(), set()
    for event in events:
        if event.get("period") in (1, 2, 3, 4) and isinstance(event.get("team"), dict):
            team = event["team"]
            tid, name = team.get("id"), team.get("name")
            if type(tid) is not int or tid <= 0 or not isinstance(name, str) or not name.strip():
                raise ValueError("Team needs a positive ID and name")
            if tid in teams and teams[tid] != name:
                raise ValueError("Conflicting team names for the same ID")
            teams[tid] = name
        if event.get("type", {}).get("name") != "Shot":
            continue
        identity = event.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Shot IDs must be present and unique")
        seen.add(identity)
        if event.get("period") not in (1, 2, 3, 4):
            excluded["non_playing_period"] += 1
            continue
        if event.get("shot", {}).get("type", {}).get("name") == "Penalty":
            excluded["penalty"] += 1
            continue
        try:
            features = shot_features(event)
        except (ValueError, TypeError):
            excluded["invalid_features"] += 1
            continue
        tid = event.get("team", {}).get("id")
        if tid not in teams:
            raise ValueError("Eligible shot has no known team")
        player = event.get("player") or {}
        rows.append({"event_id": identity, "event_index": event.get("index"), "team_id": tid,
                     "player_id": player.get("id"), "player": player.get("name"),
                     "period": event["period"], "minute": event.get("minute"), "second": event.get("second"),
                     "features": features})
    names = sorted({r["player"] for r in rows if isinstance(r["player"], str) and r["player"].strip()})
    short = _short_names(names, {})
    for row in rows:
        row["short_name"] = short.get(row["player"])
    return teams, rows, dict(excluded)


def explain_shots(model_directory, rows, protocol):
    import shap
    from xgboost import XGBClassifier
    metadata = json.loads((model_directory / "model_metadata.json").read_text(encoding="utf-8"))
    if metadata["features"] != list(FEATURES) or digest(model_directory / "model.json") != metadata["model_sha256"]:
        raise ValueError("xG model hash/features differ")
    if protocol["shap_method"] != "tree_path_dependent" or protocol["shap_output"] != "raw_log_odds":
        raise ValueError("Unsupported explanation protocol")
    model = XGBClassifier()
    model.load_model(model_directory / "model.json")
    if metadata["best_iteration"] != model.best_iteration:
        raise ValueError("xG best iteration differs from metadata")
    # TreeExplainer must explain precisely the same trees as predict_proba.
    booster = model.get_booster()[:model.best_iteration + 1]
    audit = {"method": "TreeExplainer/tree_path_dependent", "units": "log_odds",
             "shap_version": shap.__version__, "trees_explained": booster.num_boosted_rounds(),
             "model_sha256": metadata["model_sha256"], "model_metadata_sha256": digest(model_directory / "model_metadata.json"),
             "best_iteration": metadata["best_iteration"], "max_margin_error": 0., "max_probability_error": 0.}
    if not rows:
        return [], audit
    matrix = feature_matrix(pd.DataFrame([r["features"] for r in rows]))
    explainer = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent", model_output="raw")
    values = np.asarray(explainer.shap_values(matrix, check_additivity=True))
    base = float(explainer.expected_value)
    if values.shape != (len(rows), len(FEATURES)) or not np.isfinite(values).all() or not np.isfinite(base):
        raise ValueError("Invalid SHAP output")
    reconstructed = base + values.sum(axis=1)
    margins = model.predict(matrix, output_margin=True)
    probabilities = model.predict_proba(matrix)[:, 1]
    restored_probabilities = 1 / (1 + np.exp(-reconstructed))
    audit["max_margin_error"] = float(np.max(np.abs(reconstructed - margins)))
    audit["max_probability_error"] = float(np.max(np.abs(restored_probabilities - probabilities)))
    if audit["max_margin_error"] > protocol["margin_tolerance"] or audit["max_probability_error"] > protocol["probability_tolerance"]:
        raise ValueError("SHAP does not reconstruct the xG model used for inference")
    explained = [{**row, "xg": float(probability), "margin": float(margin), "base_log_odds": base,
                  "shap_log_odds": dict(zip(FEATURES, map(float, contribution)))}
                 for row, probability, margin, contribution in zip(rows, probabilities, margins, values)]
    return explained, audit


def evidence(rows, total):
    return {"event_ids": [r["event_id"] for r in rows], "subset_shots": len(rows), "team_shots": total,
            "fraction": len(rows) / total, "mean_xg": float(np.mean([r["xg"] for r in rows])),
            "mean_features": {k: float(np.mean([r["features"][k] for r in rows])) for k in FEATURES},
            "mean_shap_log_odds": {k: float(np.mean([r["shap_log_odds"][k] for r in rows])) for k in FEATURES}}


def recommend(team_id, rows, protocol):
    if len(rows) < protocol["minimum_team_shots"]:
        return [], "insufficient_data"
    cards = []
    rules = {
        "review_low_quality_shots": ([r for r in rows if r["xg"] < protocol["low_xg_threshold"]], protocol["low_xg_fraction"],
                                     "Rà soát lựa chọn vị trí dứt điểm", "Xem lại các pha có xG thấp để HLV đánh giá cách tiếp cận vị trí sút và phương án phối hợp trước đó."),
        "review_pressure_support": ([r for r in rows if r["features"]["under_pressure"] == 1], protocol["pressure_fraction"],
                                    "Rà soát hỗ trợ cầu thủ khi dứt điểm dưới áp lực", "Xem lại các pha dứt điểm dưới áp lực để đánh giá thời điểm hỗ trợ và lựa chọn nhận bóng trước cú sút."),
        "review_good_entries": ([r for r in rows if r["xg"] >= protocol["high_xg_threshold"]], protocol["high_xg_fraction"],
                                "Rà soát cách tạo cơ hội có xG cao", "Chọn các pha tạo cơ hội có xG cao để HLV xem lại và cân nhắc bài tập tái hiện phù hợp.")}
    for rule in protocol["rule_order"]:
        selected, minimum_fraction, title, action = rules[rule]
        if len(selected) < protocol["minimum_subset_shots"] or len(selected) / len(rows) < minimum_fraction:
            continue
        facts = evidence(selected, len(rows))
        means = facts["mean_shap_log_odds"]
        if rule == "review_pressure_support":
            support = ["under_pressure"] if means["under_pressure"] < 0 else []
        else:
            sign = 1 if rule == "review_good_entries" else -1
            support = [k for k in GEOMETRY if sign * means[k] > 0] if sign * sum(means[k] for k in GEOMETRY) > 0 else []
        if not support:
            continue
        cards.append({"id": f"{team_id}:{rule}", "rule": rule, "title": title, "action": action,
                      "evidence": facts, "supporting_features": support,
                      "interpretation": "SHAP giải thích dự đoán so với giá trị nền của mô hình, không chứng minh nguyên nhân hay hiệu quả can thiệp."})
    return cards, "review_suggestions" if cards else "no_rule_triggered"


def build_report(events, match_id, model_directory, protocol):
    teams, rows, excluded = collect_shots(events)
    explained, audit = explain_shots(model_directory, rows, protocol)
    summaries = []
    for tid, name in sorted(teams.items()):
        selected = [r for r in explained if r["team_id"] == tid]
        cards, status = recommend(tid, selected, protocol)
        summaries.append({"team_id": tid, "team": name, "status": status, "eligible_shots": len(selected),
                          "xg_total": float(sum(r["xg"] for r in selected)),
                          "mean_xg": float(np.mean([r["xg"] for r in selected])) if selected else None,
                          "recommendations": cards})
    return {"kind": "shot_advisor_v1", "match_id": match_id, "protocol": protocol,
            "source": "statsbomb", "timing": "post_match", "feature_labels": FEATURE_LABELS,
            "model_audit": audit, "excluded": excluded, "teams": summaries, "shots": explained,
            "limitations": ["Chỉ rà soát cú sút không penalty hiệp 1–4; không đánh giá chiến thuật toàn trận.",
                            "Ngưỡng luật là heuristic, chưa được HLV nghiệm thu; không phải mô hình học chính sách huấn luyện.",
                            "xG baseline kém StatsBomb trên test bước 6; SHAP không nâng độ chính xác của mô hình.",
                            "Các feature hình học tương quan; SHAP không phải tác động nhân quả hay chênh lệch điểm phần trăm.",
                            "Không đủ thông tin để kết luận chuyền tốt hơn sút, thay người, sơ đồ hoặc chất lượng dứt điểm."]}


def markdown_report(report):
    lines = [f"# Rà soát cơ hội dứt điểm — trận {report['match_id']}", "",
             "Bản nháp ngoại tuyến sau trận. Gợi ý để HLV xem lại, chưa được đánh giá hiệu quả chiến thuật.", ""]
    if "model_dataset_split" in report.get("provenance", {}):
        lines += [f"Trận này thuộc tập {report['provenance']['model_dataset_split']} của bước xG; không phải nghiệm thu chất lượng gợi ý độc lập.", ""]
    shots = {r["event_id"]: r for r in report["shots"]}
    for team in report["teams"]:
        lines += [f"## {team['team']}", "", f"{team['eligible_shots']} cú sút hợp lệ; tổng xG mô hình {team['xg_total']:.3f}.", ""]
        if not team["recommendations"]:
            reason = "Chưa đủ số cú sút để sinh gợi ý." if team["status"] == "insufficient_data" else "Chưa có luật nào đủ điều kiện; không đồng nghĩa đội chơi tốt."
            lines += [reason, ""]
        for card in team["recommendations"]:
            facts = card["evidence"]
            lines += [f"### {card['title']}", "", card["action"], "",
                      f"Căn cứ: {facts['subset_shots']}/{facts['team_shots']} cú sút ({facts['fraction']:.1%}), xG trung bình {facts['mean_xg']:.3f}.", "",
                      "Đóng góp SHAP trung bình của nhóm so với nền mô hình (log-odds):", ""]
            lines += [f"- {FEATURE_LABELS[k]}: giá trị feature trung bình {facts['mean_features'][k]:.3f}; SHAP {facts['mean_shap_log_odds'][k]:+.4f} log-odds." for k in card["supporting_features"]]
            lines += ["", "Một số pha minh họa (toàn bộ event ID và SHAP nằm trong advisor.json):", "",
                      "| Phút | Cầu thủ | xG | Index sự kiện |", "| --- | --- | ---: | ---: |"]
            for identity in facts["event_ids"][:3]:
                row = shots[identity]
                minute = f"{row['minute']}:{row['second']:02d}" if row["minute"] is not None and row["second"] is not None else "—"
                player = str(row["short_name"] or row["player"] or "Chưa rõ").replace("|", "\\|")
                lines += [f"| {minute} | {player} | {row['xg']:.3f} | {row['event_index']} |"]
            lines += ["", card["interpretation"], ""]
    lines += ["## Giới hạn", ""] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def run(match_id, source_directory, model_directory, output):
    source_directory, model_directory, output = map(workspace, (source_directory, model_directory, output))
    if output.exists():
        raise FileExistsError(output)
    if type(match_id) is not int or match_id <= 0:
        raise ValueError("Match ID must be positive")
    inventory = json.loads((ROOT / "docs/fixtures/xg_source_inventory_v1.json").read_text())
    protocol_path = ROOT / "docs/fixtures/advisor_protocol_v1.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    name = f"data/events/{match_id}.json"
    spec = next((s for s in inventory["files"] if s["path"] == name), None)
    if spec is None:
        raise ValueError("Match absent from pinned source inventory")
    path = source_directory / name
    check_blob(path, spec)
    metadata = json.loads((model_directory / "model_metadata.json").read_text(encoding="utf-8"))
    if metadata["protocol"]["revision"] != inventory["revision"]:
        raise ValueError("Model and source revision differ")
    matches = []
    source_specs = {item["path"]: item for item in inventory["files"]}
    for competition, season in metadata["protocol"]["development_competitions"] + metadata["protocol"]["test_competitions"]:
        relative = f"data/matches/{competition}/{season}.json"
        check_blob(source_directory / relative, source_specs[relative])
        matches += [{"match_id": m["match_id"], "match_date": m["match_date"], "competition_id": competition,
                     "season_id": season} for m in json.loads((source_directory / relative).read_text(encoding="utf-8"))]
    assignments = split_matches(matches, metadata["protocol"])
    report = build_report(json.loads(path.read_text(encoding="utf-8")), match_id, model_directory, protocol)
    report["provenance"] = {"source_revision": inventory["revision"], "events_sha256": digest(path),
                            "model_dataset_split": assignments[match_id],
                            "protocol_sha256": digest(protocol_path), "source_inventory_sha256": digest(ROOT / "docs/fixtures/xg_source_inventory_v1.json")}
    output.mkdir(parents=True)
    (output / "advisor.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "report.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"match_id": match_id, "shots": len(report["shots"]), "audit": report["model_audit"],
                      "teams": [{"team": t["team"], "shots": t["eligible_shots"], "rules": [c["rule"] for c in t["recommendations"]]} for t in report["teams"]]}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--source-directory", type=Path, default=Path("data/raw/statsbomb_xg_v1"))
    parser.add_argument("--model-directory", type=Path, default=Path("data/processed/xg_model_v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.match_id, args.source_directory, args.model_directory, args.output)
