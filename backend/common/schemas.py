from typing import Literal

from pydantic import BaseModel


class TrackingRow(BaseModel):
    frame: int
    time_s: float
    track_id: int
    team: Literal["A", "B", "referee", "unknown"]
    x_m: float
    y_m: float


class EventRow(BaseModel):
    match_id: int
    minute: int
    second: int
    team: str
    player: str | None
    event_type: str
    x_m: float | None
    y_m: float | None
    end_x_m: float | None
    end_y_m: float | None


class MetricItem(BaseModel):
    key: str
    label: str
    value: float | str
    unit: str | None
    scope: Literal["team", "player", "match"]
    subject: str | None


class AnalysisResult(BaseModel):
    source: Literal["video", "statsbomb"]
    metrics: list[MetricItem]
