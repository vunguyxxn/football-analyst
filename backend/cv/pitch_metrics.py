"""Streaming observed-track metrics, not full-match player totals."""
import math

from backend.common.schemas import AnalysisResult, MetricItem


class PitchMetrics:
    def __init__(self, fps, max_speed_kmh=40, interval_s=0.5, max_gap_s=1.0):
        self.fps = fps
        self.max_speed = max_speed_kmh
        self.interval = interval_s
        self.max_gap = max_gap_s
        self.tracks = {}

    def break_chain(self, segment, track_id):
        state = self.tracks.get((segment, track_id))
        if state is not None:
            state["anchor"] = None

    def observe(self, segment, row):
        key = (segment, row.track_id)
        state = self.tracks.setdefault(key, {"anchor": None, "distance_m": 0., "duration_s": 0.,
                                            "max_speed_kmh": 0., "rejected_steps": 0,
                                            "samples": 0, "heatmap": [[0]*21 for _ in range(14)]})
        state["samples"] += 1
        # Heatmap counts observed frames, including isolated detections; no interpolation.
        state["heatmap"][min(13, int(row.y_m/68*14))][min(20, int(row.x_m/105*21))] += 1
        previous = state["anchor"]
        if previous is None:
            state["anchor"] = row
            return
        dt = row.time_s - previous.time_s
        if dt <= 0:
            raise ValueError("Track timestamps must increase")
        if dt > self.max_gap:
            state["anchor"] = row
            return
        if dt < self.interval - 1e-9:
            return  # sample over 0.5 s to reduce frame-to-frame foot-box jitter
        distance = math.hypot(row.x_m-previous.x_m, row.y_m-previous.y_m)
        speed = distance/dt*3.6
        if speed > self.max_speed:
            state["rejected_steps"] += 1
            # Break continuity. Do not bridge a teleport or clamp it to 40 km/h.
            state["anchor"] = None
            return
        state["distance_m"] += distance
        state["duration_s"] += dt
        state["max_speed_kmh"] = max(state["max_speed_kmh"], speed)
        state["anchor"] = row

    def report(self):
        metrics, tracks = [], []
        for (segment, track_id), state in sorted(self.tracks.items()):
            subject = f"segment:{segment}/track:{track_id}"
            values = [("observed_distance", "Quãng đường quan sát hợp lệ", state["distance_m"], "m"),
                      ("observed_max_speed", "Tốc độ lớn nhất hợp lệ", state["max_speed_kmh"], "km/h"),
                      ("observed_mean_speed", "Tốc độ trung bình hợp lệ", state["distance_m"]/state["duration_s"]*3.6 if state["duration_s"] else 0, "km/h")]
            metrics.extend(MetricItem(key=key, label=label, value=value, unit=unit, scope="player", subject=subject)
                           for key, label, value, unit in values)
            tracks.append({"segment": segment, "track_id": track_id,
                           **{key: value for key, value in state.items() if key != "anchor"}})
        return {"analysis": AnalysisResult(source="video", metrics=metrics).model_dump(),
                "tracks": tracks, "heatmap": {"columns": 21, "rows": 14, "unit": "observed_frames",
                                               "origin": "bottom_left", "pitch_m": [105, 68]},
                "speed_limit_kmh": self.max_speed, "sampling_interval_s": self.interval,
                "max_gap_s": self.max_gap,
                "warning": "Partial observed tracks; ID switches, jitter and camera motion can invalidate metrics. Not player identities or full-match totals."}
