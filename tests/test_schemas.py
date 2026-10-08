import pytest
from pydantic import ValidationError

from backend.common.schemas import AnalysisResult, EventRow, MetricItem, TrackingRow


def test_tracking_row_accepts_valid_data() -> None:
    row = TrackingRow(
        frame=1,
        time_s=0.04,
        track_id=7,
        team="A",
        x_m=12.5,
        y_m=30.0,
    )
    assert row.track_id == 7


def test_tracking_row_rejects_invalid_team() -> None:
    with pytest.raises(ValidationError):
        TrackingRow(
            frame=1,
            time_s=0.04,
            track_id=7,
            team="home",
            x_m=12.5,
            y_m=30.0,
        )


def test_event_row_accepts_valid_data() -> None:
    row = EventRow(
        match_id=1,
        minute=12,
        second=34,
        team="A",
        player=None,
        event_type="Pass",
        x_m=None,
        y_m=None,
        end_x_m=None,
        end_y_m=None,
    )
    assert row.player is None


def test_event_row_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        EventRow(
            match_id="invalid",
            minute=12,
            second=34,
            team="A",
            player=None,
            event_type="Pass",
            x_m=None,
            y_m=None,
            end_x_m=None,
            end_y_m=None,
        )


def test_metric_item_accepts_valid_data() -> None:
    metric = MetricItem(
        key="possession",
        label="Kiểm soát bóng",
        value=54.2,
        unit="%",
        scope="team",
        subject="A",
    )
    assert metric.value == 54.2


def test_metric_item_rejects_invalid_scope() -> None:
    with pytest.raises(ValidationError):
        MetricItem(
            key="possession",
            label="Kiểm soát bóng",
            value=54.2,
            unit="%",
            scope="season",
            subject=None,
        )


def test_analysis_result_accepts_valid_data() -> None:
    result = AnalysisResult(
        source="video",
        metrics=[
            MetricItem(
                key="distance",
                label="Quãng đường",
                value=10.5,
                unit="km",
                scope="player",
                subject="Player 1",
            )
        ],
    )
    assert len(result.metrics) == 1


def test_analysis_result_rejects_invalid_source() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult(source="manual", metrics=[])
