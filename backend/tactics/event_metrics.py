"""Event metrics on the project's normalized StatsBomb DataFrame, in metres.

Definitions inspired by football-docs, pinned in the method catalogue. This is
an independent implementation, not a provider adapter for video tracking.
"""
from __future__ import annotations

import math

import pandas as pd

from backend.common.metric_catalog import metric_definitions
from backend.common.schemas import AnalysisResult, MetricItem
from backend.tactics.pass_network import _is_missing

RUNTIME_KEYS = tuple(card.key for card in metric_definitions() if card.implementation == "computed")


def _name(value):
    return value.get("name", "__invalid_named_value__") if isinstance(value, dict) else value


def _ratio(part: int, whole: int):
    return round(part / whole, 4) if whole else "Không có mẫu số để tính chỉ số."


def _positions_valid(rows: pd.DataFrame) -> bool:
    x = pd.to_numeric(rows["x_m"], errors="coerce")
    return bool(x.notna().all() and x.between(0, 105).all())


def _calculate(rows: pd.DataFrame, team: str, key: str):
    own = rows["team"].eq(team)
    passes = rows["event_type"].eq("Pass")
    if key in ("pass_completion.statsbomb-hudl", "ppda.statsbomb-hudl"):
        outcomes = rows.loc[passes, "pass_outcome"]
        known_outcomes = {"Incomplete", "Out", "Pass Offside", "Unknown", "Injury Clearance"}
        if not outcomes.map(lambda value: _is_missing(value) or isinstance(value, str) and value in known_outcomes).all():
            return "Sai giá trị pass_outcome; không suy đường chuyền thành công."
    if key == "pass_completion.statsbomb-hudl":
        selected = rows.loc[own & passes]
        return _ratio(int(selected["pass_outcome"].map(_is_missing).sum()), len(selected))
    if key == "xg.statsbomb-hudl":
        shots = rows.loc[own & rows["event_type"].eq("Shot")]
        xg = pd.to_numeric(shots["shot_statsbomb_xg"], errors="coerce")
        if not xg.notna().all() or not xg.between(0, 1).all():
            return "Thiếu hoặc sai xác suất xG của cú sút; không tính tổng một phần."
        return round(float(xg.sum()), 4)
    if key == "ppda.statsbomb-hudl":
        kinds = {"Pass", "Duel", "Interception", "Dribbled Past", "Foul Committed"}
        if not _positions_valid(rows.loc[rows["event_type"].isin(kinds)]):
            return "Thiếu hoặc sai vị trí sự kiện để xác định vùng PPDA."
        duels = rows.loc[own & rows["event_type"].eq("Duel"), "duel_type"]
        if duels.map(_is_missing).any():
            return "Thiếu loại Duel để xác định hành động Tackle."
        x = pd.to_numeric(rows["x_m"], errors="coerce")
        completed = rows["pass_outcome"].map(_is_missing)
        opponent_passes = (~own & passes & completed & x.lt(63)).sum()
        actions = (
            (rows["event_type"].eq("Duel") & rows["duel_type"].eq("Tackle"))
            | rows["event_type"].isin({"Interception", "Dribbled Past", "Foul Committed"})
            | (passes & rows["pass_type"].eq("Interception"))
        )
        return _ratio(int(opponent_passes), int((own & x.ge(42) & actions).sum()))
    if key == "field_tilt.stats-perform-2016":
        selected = rows.loc[passes].copy()
        if not _positions_valid(selected):
            return "Thiếu hoặc sai vị trí đường chuyền để xác định một phần ba sân."
        flags = selected["pass_cross"]
        valid_flags = flags.map(lambda v: _is_missing(v) or isinstance(v, bool) or v in ("True", "False"))
        if not valid_flags.all():
            return "Sai giá trị pass_cross; cần cờ True/False hoặc ô trống StatsBomb."
        crosses = flags.map(lambda v: False if _is_missing(v) else v in (True, "True"))
        counted = (
            pd.to_numeric(selected["x_m"], errors="coerce").ge(70)
            & ~crosses
            & ~selected["pass_type"].eq("Throw-in")
            & ~selected["pass_body_part"].eq("Keeper Arm")
        )
        return _ratio(int((counted & selected["team"].eq(team)).sum()), int(counted.sum()))
    raise ValueError(f"Unknown computed metric: {key}")


def compute_event_metrics(events: pd.DataFrame, team: str) -> AnalysisResult:
    """Return explicit unavailability for missing evidence, never partial totals.

    Empty cells in optional StatsBomb fields retain their upstream meaning.
    A missing column is different: old/trimmed caches cannot prove that field.
    """
    rows = events.copy()
    for column in ("event_type", "team", "pass_outcome", "pass_type", "duel_type", "pass_body_part"):
        if column in rows:
            rows[column] = rows[column].map(_name)
    base_error = None
    if not {"event_type", "team", "period"}.issubset(rows):
        base_error = "Thiếu loại sự kiện, đội hoặc hiệp đấu; không suy dữ liệu toàn trận."
    else:
        periods = pd.to_numeric(rows["period"], errors="coerce")
        if not periods.isin([1, 2, 3, 4, 5]).all():
            base_error = "Thiếu hoặc sai hiệp đấu; không thể loại luân lưu."
        else:
            rows = rows.loc[periods.isin([1, 2, 3, 4])].copy()
            valid_names = lambda series: series.map(lambda v: isinstance(v, str) and bool(v.strip())).all()
            if not valid_names(rows["team"]) or not valid_names(rows["event_type"]):
                base_error = "Thiếu đội hoặc loại sự kiện trong dữ liệu."
            elif team not in set(rows["team"]):
                raise ValueError("Đội được chọn không có sự kiện thi đấu trong trận này.")
            elif rows["team"].nunique() != 2:
                base_error = "Cần dữ liệu sự kiện của đúng hai đội để phân tích trận."
            elif "match_id" in rows and (rows["match_id"].isna().any() or rows["match_id"].nunique() != 1):
                base_error = "Dữ liệu thiếu mã trận hoặc trộn nhiều trận đấu."
    result = []
    for card in metric_definitions():
        if card.key not in RUNTIME_KEYS:
            continue
        missing = sorted(set(card.required_columns) - set(rows.columns))
        if base_error:
            value = base_error
        elif missing:
            value = "Thiếu trường dữ liệu: " + ", ".join(missing)
        else:
            value = _calculate(rows, team, card.key)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite event metric")
        result.append(MetricItem(key=card.key, label=card.label, value=value,
                                 unit=card.unit, scope="team", subject=team))
    return AnalysisResult(source="statsbomb", metrics=result)
