"""Versioned method cards; separate from the unchanged result schemas."""
from functools import lru_cache
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    version: int
    label: str
    unit: str | None
    source: Literal["statsbomb", "video"]
    implementation: Literal["computed", "documented"]
    mapping: Literal["same-provider", "approximation", "project"]
    formula: str
    required_columns: list[str]
    interpretation: str
    caveats: list[str]
    source_url: str
    reference_url: str


@lru_cache(maxsize=1)
def metric_definitions() -> tuple[MetricDefinition, ...]:
    payload = json.loads(Path(__file__).with_name("metric_catalog.json").read_text(encoding="utf-8"))
    definitions = tuple(MetricDefinition.model_validate(card) for card in payload)
    if len({card.key for card in definitions}) != len(definitions):
        raise ValueError("Duplicate metric definition key")
    return definitions


def metric_definition(key: str) -> MetricDefinition:
    return next(card for card in metric_definitions() if card.key == key)
