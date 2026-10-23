"""Audit agent draft spatial labels; never treat them as independent truth."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path

from backend.tactics.evaluate_formation import compare_metrica_reports


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def window_key(row):
    return row["game"], row["period"], row["team"], row["start_s"], row["stop_s"]


def validate_review(packet, review):
    if review.get("kind") != "agent_formation_review_v1" or review.get("human_reviewed") is not False or review.get("independent_ground_truth") is not False:
        raise ValueError("Agent review must retain explicit non-independent provenance")
    if review.get("source_packet_canonical_sha256") != canonical_hash(packet):
        raise ValueError("Review source packet hash mismatch")
    windows = {}
    for report in packet["reports"]:
        for team in report["teams"]:
            for window in team["formation_windows"]:
                key = (report["game"], report["period"], team["team"], window["start_s"], window["stop_s"])
                if key in windows:
                    raise ValueError("Duplicate source window")
                windows[key] = (team, window)
    seen = set()
    for row in review["rows"]:
        key = window_key(row)
        if key in seen or key not in windows:
            raise ValueError("Duplicate or foreign review window")
        seen.add(key)
        team, window = windows[key]
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise ValueError("Every review decision needs a reason")
        if row["status"] == "draft_shape":
            players = {p["track_id"] for p in window.get("players", [])}
            outfield = players - {team["goalkeeper_id"]}
            try:
                counts = [int(v) for v in row["shape"].split("-")]
            except (AttributeError, ValueError):
                raise ValueError("Invalid draft shape") from None
            flattened = [p for line in row["lines"] for p in line]
            if len(outfield) != 10 or team["goalkeeper_id"] not in players or sum(counts) != 10 or min(counts) < 1 or [len(line) for line in row["lines"]] != counts or len(flattened) != 10 or set(flattened) != outfield:
                raise ValueError("Draft lines must assign every outfield player exactly once")
            snapshots = row.get("snapshots", [])
            if len(snapshots) != 3 or len({s["frame"] for s in snapshots}) != 3:
                raise ValueError("Draft shape requires three distinct source snapshots")
            fps = next(s["loader_audit"]["fps"] for report in packet["reports"] if report["game"] == key[0]
                       for s in report["sources"] if s["team"] == key[2])
            for previous, current in zip(snapshots, snapshots[1:]):
                if current["frame"] <= previous["frame"] or current["time_s"] <= previous["time_s"] or abs((current["frame"] - previous["frame"]) / fps - (current["time_s"] - previous["time_s"])) > 1e-5:
                    raise ValueError("Snapshot order/cadence mismatch")
            for snapshot in snapshots:
                samples = snapshot["players"]
                if not isinstance(snapshot["frame"], int) or not key[3] <= snapshot["time_s"] < key[4] or len(samples) != 11 or {p["track_id"] for p in samples} != players:
                    raise ValueError("Invalid snapshot time or roster")
                for sample in samples:
                    xy = sample["xy_m"]
                    if len(xy) != 2 or not all(math.isfinite(v) for v in xy) or not (0 <= xy[0] <= 105 and 0 <= xy[1] <= 68):
                        raise ValueError("Invalid snapshot coordinates")
        elif row["status"] in ("unscorable", "insufficient_data"):
            if row.get("shape") is not None or row.get("lines"):
                raise ValueError("Unscorable windows cannot supply a true unknown label")
            if (row["status"] == "insufficient_data") != (not window.get("players")):
                raise ValueError("Review data availability conflicts with source")
        else:
            raise ValueError("Unsupported review status")
    if seen != set(windows):
        raise ValueError("Review must account for every source window")


def evaluate_review(packet, review):
    validate_review(packet, review)
    predictions = {window_key(row): row for row in compare_metrica_reports(packet["reports"])["windows"]}
    rows = []
    for annotation in review["rows"]:
        key = window_key(annotation)
        row = {k: annotation[k] for k in ("game", "period", "team", "start_s", "stop_s", "status", "shape", "reason")}
        for method in ("gap", "template"):
            predicted = predictions[key][method].get("shape")
            outcome = "unassessed"
            if annotation["status"] == "draft_shape":
                outcome = "abstained" if predicted is None else "agrees_with_draft" if predicted == annotation["shape"] else "disagrees_with_draft"
            row[method] = {"shape": predicted, "outcome": outcome}
        rows.append(row)
    summary = {method: dict(Counter(r[method]["outcome"] for r in rows)) for method in ("gap", "template")}
    return {"kind": "agent_formation_agreement_v1", "reviewer": review["reviewer"],
            "human_reviewed": False, "independent_ground_truth": False,
            "target": review["target"], "source_packet_canonical_sha256": canonical_hash(packet),
            "review_canonical_sha256": canonical_hash(review),
            "review_status_counts": dict(Counter(r["status"] for r in rows)),
            "agreement_counts": summary, "windows": rows,
            "warning": "Agent draft agreement only. Unscorable is not a true unknown class. No tactical accuracy claim."}


def render_sheets(packet, review, output):
    # Local QA plots only, not an API image response.
    os.environ["MPLCONFIGDIR"] = str(Path(__file__).resolve().parents[2] / ".tmp/matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def draw(ax, players, goalkeeper, title):
        ax.set(xlim=(0, 105), ylim=(0, 68), title=title, xlabel="x (m)", ylabel="y (m)")
        ax.grid(alpha=.25)
        for p in players:
            x, y = p.get("median_position_m", p.get("xy_m"))
            gk = p["track_id"] == goalkeeper
            ax.scatter(x, y, c="green" if gk else "navy", marker="s" if gk else "o")
            ax.annotate(str(p["track_id"]), (x, y), xytext=(3, 3), textcoords="offset points", fontsize=8)
        if not players:
            ax.text(52, 34, "Insufficient joint observations", ha="center")

    goalkeepers = {}
    for report in packet["reports"]:
        for team in report["teams"]:
            goalkeepers[(report["game"], team["team"])] = team["goalkeeper_id"]
            fig, axes = plt.subplots(3, 2, figsize=(13, 12))
            for ax, window in zip(axes.flat, team["formation_windows"]):
                draw(ax, window.get("players", []), team["goalkeeper_id"],
                     f"G{report['game']} {team['team']} {window['start_s']}-{window['stop_s']}s; attack {team['attack_direction']:+d}")
            fig.suptitle("Median positions only; green square = goalkeeper; no predictions")
            fig.tight_layout()
            fig.savefig(output / f"game{report['game']}_{team['team']}_positions.png", dpi=140)
            plt.close(fig)
    for row in review["rows"]:
        if row["status"] != "draft_shape":
            continue
        fig, axes = plt.subplots(1, 3, figsize=(16, 4))
        for ax, snapshot in zip(axes, row["snapshots"]):
            draw(ax, snapshot["players"], goalkeepers[(row["game"], row["team"])],
                 f"G{row['game']} {row['team']} {snapshot['time_s']:.2f}s")
        fig.suptitle("Native full-roster snapshots; no predictions or inferred line membership")
        fig.tight_layout()
        fig.savefig(output / f"game{row['game']}_{row['team']}_{row['start_s']}_snapshots.png", dpi=120)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        parser.error("Output must be a new directory inside project")
    packet = json.loads((root / "docs/fixtures/metrica_formation_windows.json").read_text(encoding="utf-8"))
    review = json.loads((root / "docs/fixtures/metrica_formation_agent_review.json").read_text(encoding="utf-8"))
    result = evaluate_review(packet, review)
    output.mkdir(parents=True)
    (output / "evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    text = ["# Rà soát hình dạng đội hình — nhãn nháp của agent", "",
            "Chưa được người đánh giá độc lập xác nhận. Không phải độ chính xác chiến thuật.", "",
            "| Trận/đội/thời gian | Trạng thái tham chiếu nháp | Gap | Template |", "|---|---|---|---|"]
    for row in result["windows"]:
        reference = row["shape"] or row["status"]
        text.append(f"| G{row['game']} {row['team']} {row['start_s']}-{row['stop_s']}s | {reference} | {row['gap']['shape'] or 'chưa xác định'} | {row['template']['shape'] or 'chưa xác định'} |")
    (output / "review.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    if args.render:
        render_sheets(packet, review, output)
    print(json.dumps({"review_status_counts": result["review_status_counts"],
                      "agreement_counts": result["agreement_counts"]}))


if __name__ == "__main__":
    main()
