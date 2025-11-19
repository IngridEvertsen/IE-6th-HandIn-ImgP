"""
WHAT THIS SCRIPT DOES:
--------------------------------------------------------------------------------------
- Exercise-specific logic for counting squats.
  - This module contains a :class:`SquatCounter` that consumes pose landmarks and
    emits state transitions + repetition counts so that other modules (sound and
    UI) can react to user movement.
--------------------------------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple
import numpy as np

Landmark = Tuple[float, float]
LandmarkMap = Mapping[str, Landmark]


@dataclass
# Container describing the result of a counter update.
class SquatEvent:

    angle: float
    state: str
    rep_completed: bool


class SquatCounter:
    """
    Counts squat repetitions using hip/knee/ankle landmarks.

    Parameters
    ----------
    side:
        Body side to evaluate. Valid values are ``"left"`` or ``"right"``.
    down_angle:
        Knee angle (degrees) that marks the *bottom* of a squat. Once the
        current angle dips below this value the state transitions to "down".
    up_angle:
        Knee angle threshold for the *top* of a squat. Once the user returns
        above this angle while previously in the "down" state, the counter
        increments and the state flips back to "up".
    min_movement:
        Minimum angular delta (degrees) before we consider a transition. This
        avoids rapid flickering around threshold values.
    """

    def __init__
    (
        self,
        side: str = "left",
        down_angle: float = 70.0,
        up_angle: float = 160.0,
        min_movement: float = 5.0,
    ) -> None:
        if side not in {"left", "right"}:
            raise ValueError("Side must be 'left' or 'right'.")
        self.side = side
        self.down_angle = down_angle
        self.up_angle = up_angle
        self.min_movement = min_movement

        self.rep_count = 0
        self.state = "up"
        self._last_angle: Optional[float] = None

    @staticmethod
    def _angle(a: Landmark, b: Landmark, c: Landmark) -> float:
        """Return the angle ABC (with B as the vertex) in degrees."""

        a_vec = np.array(a, dtype=np.float64)
        b_vec = np.array(b, dtype=np.float64)
        c_vec = np.array(c, dtype=np.float64)

        ba = a_vec - b_vec
        bc = c_vec - b_vec

        ba_norm = np.linalg.norm(ba)
        bc_norm = np.linalg.norm(bc)
        if ba_norm == 0.0 or bc_norm == 0.0:
            return float("nan")

        cosine = np.dot(ba, bc) / (ba_norm * bc_norm)
        cosine = np.clip(cosine, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine)))

    def reset(self) -> None:
        """Reset the repetition count and state."""

        self.rep_count = 0
        self.state = "up"
        self._last_angle = None

    def _get_landmark(self, landmarks: LandmarkMap, name: str) -> Landmark:
        key = f"{self.side}_{name}"
        if key in landmarks:
            return landmarks[key]
        if name in landmarks:
            return landmarks[name]
        raise KeyError(f"Missing landmark '{key}' in input")

    def update(self, landmarks: LandmarkMap) -> SquatEvent:
        """Consume pose landmarks and update repetition state.

        Parameters
        ----------
        landmarks:
            Mapping of landmark names to 2D coordinates. The mapping must
            contain hip/knee/ankle points for the configured ``side``.
        """

        try:
            hip = self._get_landmark(landmarks, "hip")
            knee = self._get_landmark(landmarks, "knee")
            ankle = self._get_landmark(landmarks, "ankle")
        except KeyError:
            # If any landmark is missing we cannot compute the angle. Return the
            # last known state without counting a repetition.
            angle = float("nan")
            return SquatEvent(angle=angle, state=self.state, rep_completed=False)

        angle = self._angle(hip, knee, ankle)
        if np.isnan(angle):
            return SquatEvent(angle=angle, state=self.state, rep_completed=False)

        last_angle = self._last_angle
        self._last_angle = angle
        rep_completed = False

        if last_angle is not None and abs(angle - last_angle) < self.min_movement:
            # Ignore negligible changes to avoid flickering around thresholds.
            return SquatEvent(angle=angle, state=self.state, rep_completed=False)

        if self.state == "up" and angle <= self.down_angle:
            self.state = "down"
        elif self.state == "down" and angle >= self.up_angle:
            self.state = "up"
            self.rep_count += 1
            rep_completed = True

        return SquatEvent(angle=angle, state=self.state, rep_completed=rep_completed)


__all__ = ["SquatCounter", "SquatEvent"]

