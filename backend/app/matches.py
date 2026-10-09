from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from requests.exceptions import RequestException

from backend.tactics import loader
from backend.tactics.loader import MatchNotFoundError
from backend.tactics.pass_network import compute_pass_network

router = APIRouter(prefix="/api/matches", tags=["matches"])


class CompetitionResponse(BaseModel):
    competition_id: int
    season_id: int
    competition_name: str
    season_name: str
    country_name: str | None = None


class MatchResponse(BaseModel):
    match_id: int
    match_date: str | None = None
    kick_off: str | None = None
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    competition_stage: str | None = None


class PassNetworkNodeResponse(BaseModel):
    player: str
    avg_x_m: float
    avg_y_m: float
    pass_count: int
    touches: int


class PassNetworkEdgeResponse(BaseModel):
    source: str
    target: str
    count: int


class PassNetworkResponse(BaseModel):
    nodes: list[PassNetworkNodeResponse]
    edges: list[PassNetworkEdgeResponse]


def _record_value(record: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None and not pd.isna(value):
            return value
    return None


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.index.name and frame.index.name not in frame.columns:
        frame = frame.reset_index()
    return frame.to_dict(orient="records")


def _as_int(value: Any, field: str) -> int:
    if value is None:
        raise ValueError(f"StatsBomb response is missing {field}")
    return int(value)


def _as_text(value: Any, field: str) -> str:
    if value is None:
        raise ValueError(f"StatsBomb response is missing {field}")
    return str(value)


@router.get("/competitions", response_model=list[CompetitionResponse])
def get_competitions() -> list[CompetitionResponse]:
    try:
        records = _records(loader.list_competitions())
        return [
            CompetitionResponse(
                competition_id=_as_int(
                    _record_value(record, "competition_id", "id"), "competition_id"
                ),
                season_id=_as_int(_record_value(record, "season_id"), "season_id"),
                competition_name=_as_text(
                    _record_value(record, "competition_name"), "competition_name"
                ),
                season_name=_as_text(_record_value(record, "season_name"), "season_name"),
                country_name=_record_value(record, "country_name"),
            )
            for record in records
        ]
    except RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"StatsBomb Open Data unavailable: {error}",
        ) from error


@router.get("", response_model=list[MatchResponse])
def get_matches(
    competition_id: int = Query(...),
    season_id: int = Query(...),
) -> list[MatchResponse]:
    try:
        records = _records(loader.list_matches(competition_id, season_id))
        return [
            MatchResponse(
                match_id=_as_int(_record_value(record, "match_id", "id"), "match_id"),
                match_date=(
                    str(_record_value(record, "match_date"))
                    if _record_value(record, "match_date") is not None
                    else None
                ),
                kick_off=(
                    str(_record_value(record, "kick_off"))
                    if _record_value(record, "kick_off") is not None
                    else None
                ),
                home_team=_as_text(
                    _record_value(record, "home_team", "home_team_name"), "home_team"
                ),
                away_team=_as_text(
                    _record_value(record, "away_team", "away_team_name"), "away_team"
                ),
                home_score=(
                    int(_record_value(record, "home_score"))
                    if _record_value(record, "home_score") is not None
                    else None
                ),
                away_score=(
                    int(_record_value(record, "away_score"))
                    if _record_value(record, "away_score") is not None
                    else None
                ),
                competition_stage=_record_value(record, "competition_stage"),
            )
            for record in records
        ]
    except RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"StatsBomb Open Data unavailable: {error}",
        ) from error


@router.get(
    "/{match_id}/pass-network",
    response_model=PassNetworkResponse,
)
def get_pass_network(
    match_id: int,
    team: str = Query(..., min_length=1),
) -> dict[str, list[dict[str, Any]]]:
    try:
        events = loader.load_events(match_id)
    except MatchNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return compute_pass_network(events, team)
