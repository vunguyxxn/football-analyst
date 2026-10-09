from __future__ import annotations

import importlib.util
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from requests.exceptions import HTTPError
from statsbombpy import sb

from backend.common.pitch import statsbomb_to_pitch

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
COORDINATE_EVENT_TYPES = {"Pass", "Carry", "Shot"}


class MatchNotFoundError(LookupError):
    """Raised when a match is not present in StatsBomb Open Data."""


@contextmanager
def _suppress_credentials_warning() -> Generator[None, None, None]:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="credentials were not supplied\\. open data access only",
            category=UserWarning,
        )
        yield


def list_competitions() -> pd.DataFrame:
    """Return competitions available through StatsBomb Open Data."""
    with _suppress_credentials_warning():
        return sb.competitions()


def list_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """Return open-data matches for a competition and season."""
    with _suppress_credentials_warning():
        matches = sb.matches(
            competition_id=competition_id,
            season_id=season_id,
        )
    if matches.index.name and matches.index.name not in matches.columns:
        matches = matches.reset_index()
    return matches


def _named_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("name")
    return value


def _coordinates(value: Any) -> tuple[float | None, float | None]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None, None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None, None


def normalize_events(events: pd.DataFrame, match_id: int) -> pd.DataFrame:
    """Convert StatsBomb events to the shared EventRow coordinate conventions.

    StatsBomb's original fields such as ``pass_outcome`` and ``pass_recipient``
    are retained because downstream tactics calculations need them.
    """
    normalized = events.copy()
    if "event_type" not in normalized.columns:
        source_type = normalized["type"] if "type" in normalized else "Unknown"
        if isinstance(source_type, str):
            normalized["event_type"] = source_type
        else:
            normalized["event_type"] = source_type.map(_named_value)
    else:
        normalized["event_type"] = normalized["event_type"].map(_named_value)

    normalized["match_id"] = match_id
    if "minute" not in normalized:
        normalized["minute"] = 0
    if "second" not in normalized:
        normalized["second"] = 0
    normalized["minute"] = pd.to_numeric(normalized["minute"], errors="coerce").fillna(0).astype(int)
    normalized["second"] = pd.to_numeric(normalized["second"], errors="coerce").fillna(0).astype(int)

    for normalized_name, source_name in (("team", "team"), ("player", "player")):
        if source_name not in normalized:
            normalized[normalized_name] = None
        else:
            normalized[normalized_name] = normalized[source_name].map(_named_value)

    starts = normalized["location"].map(_coordinates) if "location" in normalized else pd.Series(
        [(None, None)] * len(normalized), index=normalized.index
    )
    normalized["x_m"] = starts.map(
        lambda point: statsbomb_to_pitch(*point)[0] if point[0] is not None else None
    )
    normalized["y_m"] = starts.map(
        lambda point: statsbomb_to_pitch(*point)[1] if point[1] is not None else None
    )

    ends = normalized["end_location"].map(_coordinates) if "end_location" in normalized else pd.Series(
        [(None, None)] * len(normalized), index=normalized.index
    )
    uses_end_location = normalized["event_type"].isin(COORDINATE_EVENT_TYPES)
    normalized["end_x_m"] = [
        statsbomb_to_pitch(*point)[0] if use_end and point[0] is not None else None
        for point, use_end in zip(ends, uses_end_location)
    ]
    normalized["end_y_m"] = [
        statsbomb_to_pitch(*point)[1] if use_end and point[0] is not None else None
        for point, use_end in zip(ends, uses_end_location)
    ]

    for field in ("pass_outcome", "pass_recipient"):
        if field in normalized:
            normalized[field] = normalized[field].map(_named_value)
    return normalized.drop(columns=["location", "end_location"], errors="ignore")


def _cache_paths(match_id: int) -> tuple[Path, Path]:
    return (
        PROCESSED_DATA_DIR / f"events_{match_id}.parquet",
        PROCESSED_DATA_DIR / f"events_{match_id}.csv",
    )


def load_events(match_id: int) -> pd.DataFrame:
    """Load and normalize a match, caching it locally for subsequent calls.

    Parquet is used when pyarrow is installed; otherwise CSV is used. Existing
    caches of either supported format are reused.
    """
    parquet_path, csv_path = _cache_paths(match_id)
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)

    try:
        with _suppress_credentials_warning():
            raw_events = sb.events(match_id=match_id)
    except (FileNotFoundError, HTTPError) as error:
        if isinstance(error, HTTPError) and (
            error.response is None or error.response.status_code != 404
        ):
            raise
        raise MatchNotFoundError(f"Match {match_id} was not found") from error
    if raw_events.empty:
        raise MatchNotFoundError(f"Match {match_id} was not found")

    normalized = normalize_events(raw_events, match_id)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if importlib.util.find_spec("pyarrow") is not None:
        normalized.to_parquet(parquet_path, index=False)
    else:
        normalized.to_csv(csv_path, index=False)
    return normalized
