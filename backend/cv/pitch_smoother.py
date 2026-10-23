"""Causal robust footpoint estimates; rejected jumps never become speed clamps."""
from collections import deque
from dataclasses import dataclass, field
import math

import numpy as np


@dataclass
class _Track:
    last: object
    seen: float
    history: deque = field(default_factory=deque)
    interrupted: bool = False
    confirmed: bool = False


class PitchSmoother:
    window_s = 0.2
    max_gap_s = 0.25
    min_span_s = 0.08
    noise_margin_m = 0.5
    max_speed_kmh = 40
    method = "causal_linear_endpoint_v2_1"

    def __init__(self):
        self.tracks = {}

    def advance(self, time_s):
        for key in list(self.tracks):
            if time_s - self.tracks[key].seen > 1:
                del self.tracks[key]

    def _reachable(self, previous, row):
        # Rejected observations cannot make the acceptance radius grow forever.
        # A new location needs an actual observation gap, new ID or calibration
        # segment; repetition at a distant location is not evidence of identity.
        dt = min(row.time_s - previous.time_s, self.max_gap_s)
        distance = math.hypot(row.x_m - previous.x_m, row.y_m - previous.y_m)
        return distance <= self.max_speed_kmh / 3.6 * dt + self.noise_margin_m

    def observe(self, segment, row):
        """Return (filtered row or None, break metric continuity, status)."""
        key = (segment, row.track_id)
        state = self.tracks.get(key)
        reset = state is None
        if state is not None and row.time_s <= state.seen:
            raise ValueError("Track timestamps must increase")
        if state is None or row.time_s - state.seen > self.max_gap_s:
            state = self.tracks[key] = _Track(row, row.time_s)
            reset = True
        state.seen = row.time_s
        if not self._reachable(state.last, row):
            if not state.confirmed:
                # No published coordinate anchors this tentative chain yet.
                # Restart warm-up rather than locking onto its first outlier.
                state = self.tracks[key] = _Track(row, row.time_s)
                reset = True
            else:
                state.interrupted = True
                state.history.clear()
                return None, True, "jump_rejected"
        if state.interrupted:
            reset = True
            state.interrupted = False
        state.last = row
        state.history.append(row)
        while state.history and row.time_s - state.history[0].time_s > self.window_s + 1e-9:
            state.history.popleft()
        history = list(state.history)
        if len(history) < 3 or row.time_s - history[0].time_s < self.min_span_s - 1e-9:
            return None, reset, "warming_up"
        # Fit only past/current samples and evaluate at the current timestamp.
        # Unlike a moving average this exactly reproduces constant velocity.
        # Endpoint regression can overshoot turns/stops; never clamp that into
        # an apparently valid pitch position or a capped speed.
        times = np.array([r.time_s - row.time_s for r in history])
        points = np.array([[r.x_m, r.y_m] for r in history])
        centered = times - times.mean()
        slope = centered @ points / (centered @ centered)
        x, y = points.mean(axis=0) - slope * times.mean()
        if not np.isfinite([x, y]).all() or not (0 <= x <= 105 and 0 <= y <= 68):
            state.history = deque([row])
            return None, True, "filtered_outside"
        state.confirmed = True
        return row.model_copy(update={"x_m": float(x), "y_m": float(y)}), reset, "accepted"
