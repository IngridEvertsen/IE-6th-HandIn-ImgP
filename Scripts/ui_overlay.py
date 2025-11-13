"""
WHAT THIS SCRIPT DOES:
--------------------------------------------------------------------------------------
- Provides a small, well-documented ``UIOverlay`` helper that draws a workout HUD (Heads-Up Display).

- Renders a configurable status bar containing repetition counts, current joint
  angles, and the state reported by the exercise logic ("down" vs. "up").

- Offers tiny convenience helpers that make it easy to annotate frames with
  pose landmarks whenever you need to debug detector output.
--------------------------------------------------------------------------------------
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import cv2

Color = Tuple[int, int, int]


@dataclass
class UIOverlay:
    """Utility class that handles all drawing logic for the workout HUD.

    The previous iteration bundled several magic numbers and hard-coded
    operations in ``draw_hud``.  This class keeps the same public API but the
    internals are decomposed into small helpers so the drawing steps are easy to
    follow and tweak.
    """

    window_name: str = "Fitness Helper"
    background_color: Color = (0, 0, 0)
    text_color: Color = (255, 255, 255)
    accent_color: Color = (0, 255, 0)
    alert_color: Color = (0, 128, 255)
    hud_height: int = 80

    # ------ Public helpers ------
    def draw_hud(
        self,
        frame,
        rep_count: int,
        angle: Optional[float],
        state: str,
        rep_completed: bool = False,
    ) -> None:
        """Paint the top HUD bar with repetition/angle/state information."""

        height, width = frame.shape[:2]
        self._draw_background(frame, width)

        angle_text = self._format_angle(angle)
        state_text = state.capitalize()

        self._put_text(frame, f"Reps: {rep_count}", (20, 30), 0.9)
        self._put_text(frame, f"Angle: {angle_text}", (20, 60), 0.7)

        color = self.alert_color if rep_completed else self.accent_color
        # Right-align the state label by starting near the far edge.
        self._put_text(frame, f"State: {state_text}", (width - 220, 30), 0.8, color)

    def draw_landmarks(self, frame, landmarks: Dict[str, Tuple[float, float]]) -> None:
        """Render pose landmarks as simple points to aid debugging."""

        for point in landmarks.values():
            x, y = map(int, point)
            cv2.circle(frame, (x, y), 4, self.accent_color, -1)

    
    # ------ Private helpers ------
    def _draw_background(self, frame, width: int) -> None:
        cv2.rectangle(frame, (0, 0), (width, self.hud_height), self.background_color, -1)

    def _format_angle(self, angle: Optional[float]) -> str:
        if angle is None or angle != angle:  # guard NaN
            return "--"
        return f"{angle:.1f}°"

    def _put_text(
        self,
        frame,
        text: str,
        origin: Tuple[int, int],
        scale: float,
        color: Optional[Color] = None,
    ) -> None:
        cv2.putText(
            frame,
            text,
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color or self.text_color,
            2,
            cv2.LINE_AA,
        )


__all__ = ["UIOverlay"]

