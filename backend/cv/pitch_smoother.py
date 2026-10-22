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
    pending: deque = field(default_factory=lambda: deque(maxlen=3))
    estimate: object = None
    estimate_time: float = 0


class PitchSmoother:
    window_s = 0.2
    max_gap_s = 0.25
    min_span_s = 0.08
    noise_margin_m = 0.5
    max_speed_kmh = 40
    time_constant_s = 0.08

    def __init__(self):
        self.tracks = {}

    def advance(self, time_s):
        for key in list(self.tracks):
            if time_s - self.tracks[key].seen > 1:
                del self.tracks[key]

    def _reachable(self, previous, row):
        dt = row.time_s - previous.time_s
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
            if state.pending and not self._reachable(state.pending[-1], row):
                state.pending.clear()
            state.pending.append(row)
            if len(state.pending) < 3:
                return None, True, "jump_rejected"
            # Confirm a new local chain without bridging to the old location.
            state.history = deque(state.pending)
            state.estimate = np.median([[r.x_m, r.y_m] for r in state.pending], axis=0)
            state.estimate_time = row.time_s
            state.pending.clear()
            state.last = row
            return None, True, "reacquiring"
        state.pending.clear()
        state.last = row
        state.history.append(row)
        while state.history and row.time_s - state.history[0].time_s > self.window_s + 1e-9:
            state.history.popleft()
        history = list(state.history)
        # Median of three observed footpoints rejects small isolated spikes.
        # A time-based EMA reduces jitter with an explicit, measurable lag.
        point = np.median([[r.x_m, r.y_m] for r in history[-3:]], axis=0)
        if state.estimate is None:
            state.estimate = point
        else:
            alpha = 1 - math.exp(-(row.time_s - state.estimate_time) / self.time_constant_s)
            state.estimate = state.estimate + alpha * (point - state.estimate)
        state.estimate_time = row.time_s
        if len(history) < 3 or row.time_s - history[0].time_s < self.min_span_s - 1e-9:
            return None, reset, "warming_up"
        x, y = state.estimate
        if not np.isfinite([x, y]).all() or not (0 <= x <= 105 and 0 <= y <= 68):
            state.history = deque([row])
            return None, True, "filtered_outside"
        return row.model_copy(update={"x_m": float(x), "y_m": float(y)}), reset, "accepted"
