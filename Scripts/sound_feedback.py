'''
WHAT THIS FILE DOES
------------------------------------------------------------
- Provides a simple speak() function for short voice prompts.
- On macOS, it uses the built-in "say" command (no setup needed).
- On other systems, it just prints the text (you still see the feedback).
- It also rate-limits messages so you don't get spammed.
------------------------------------------------------------
'''

from __future__ import annotations

import platform
import subprocess
import time

_IS_MAC = platform.system() == "Darwin"
_enabled = True
_last_ts = 0.0
_MIN_GAP = 3  # minimum seconds between spoken messages (avoid spam)


def set_enabled(flag: bool) -> None:
    """Turn voice output on or off at runtime."""

    global _enabled
    _enabled = bool(flag)


def speak(text: str) -> None:
    """Say a short phrase (rate-limited so feedback stays pleasant)."""

    global _last_ts
    if not _enabled:
        return
    now = time.time()
    if (now - _last_ts) < _MIN_GAP:
        return
    _last_ts = now

    if _IS_MAC:
        try:
            subprocess.Popen(["say", text])  # fire-and-forget
        except Exception:
            print("[voice]", text)
    else:
        print("[voice]", text)


class SoundFeedback:
    """Small helper that wraps :func:`speak` with workout-specific phrasing."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        positive_prompt: str = "Great job",
    ) -> None:
        self.positive_prompt = positive_prompt
        self.set_enabled(enabled)

    def set_enabled(self, flag: bool) -> None:
        set_enabled(flag)

    def announce_repetition(self, count: int) -> None:
        speak(f"{self.positive_prompt}! That's {count} reps.")


__all__ = ["set_enabled", "speak", "SoundFeedback"]
