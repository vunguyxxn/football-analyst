PITCH_LENGTH_M = 105
PITCH_WIDTH_M = 68


def statsbomb_to_pitch(x: float, y: float) -> tuple[float, float]:
    """Convert StatsBomb 120x80 top-left coordinates to the standard pitch."""
    x_m = x * PITCH_LENGTH_M / 120
    y_m = (80 - y) * PITCH_WIDTH_M / 80
    return x_m, y_m
