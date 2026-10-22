"""Bounded, causal voting of jersey roles within each observed tracker ID."""
from collections import Counter, deque
import math


class TrackRoleSmoother:
    def __init__(self, fps: float):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("FPS must be positive and finite")
        self.window_frames = max(3, math.ceil(fps * 0.5))
        self.min_votes = max(3, math.ceil(fps * 0.1))
        self.histories = {}
        self.frame = -1

    def advance(self, frame: int):
        """Age tracks even on frames with no detections or invalid pitch geometry."""
        if frame < self.frame:
            raise ValueError("Frames must not go backwards")
        self.frame = frame
        for track_id in list(self.histories):
            if frame - self.histories[track_id][-1][0] >= self.window_frames:
                del self.histories[track_id]

    def update(self, frame: int, track_id: int, role: str) -> str:
        if role not in ("A", "B", "referee", "unknown"):
            raise ValueError("Invalid jersey role")
        if frame != self.frame:
            self.advance(frame)
        history = self.histories.setdefault(track_id, deque())
        if history and history[-1][0] >= frame:
            raise ValueError("A track may be observed only once per frame")
        while history and frame - history[0][0] >= self.window_frames:
            history.popleft()
        history.append((frame, role))
        # Unknown observations count against confidence, never vote for a team.
        votes = Counter(value for _, value in history if value != "unknown")
        if not votes:
            return "unknown"
        winner, support = votes.most_common(1)[0]
        if support < self.min_votes or support / len(history) < 0.7 or role != winner:
            return "unknown"
        return winner
