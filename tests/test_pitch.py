import pytest

from backend.common.pitch import statsbomb_to_pitch


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        (0, 0, (0, 68)),
        (120, 80, (105, 0)),
        (60, 40, (52.5, 34)),
    ],
)
def test_statsbomb_to_pitch(
    x: float, y: float, expected: tuple[float, float]
) -> None:
    assert statsbomb_to_pitch(x, y) == pytest.approx(expected)
