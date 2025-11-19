"""
audio_feedback.py

Purpose:
--------
This script defines a small "AudioCoach" class that handles:
    - Spoken feedback when the user performs good squats.
    - Motivational phrases ("Well done", "Nice depth", etc.).
    - Simple rep counting messages ("That's 5 reps", "10 to go", etc.).

We use macOS' built-in 'say' command instead of a Python TTS library,
because it is extremely reliable in a virtual environment and easy to demo.
"""

import threading
import random
import time
import subprocess
import shutil


class AudioCoach:
    """
    Handles all speaking logic using macOS' 'say' command.

    We run each message in a small background thread so that
    the main video loop (OpenCV) never freezes while audio is playing.
    """

    def __init__(self, target_reps=20, speak_delay=0.7):
        self.target_reps = target_reps
        self.speak_delay = speak_delay  # short pause so we don't spam too fast

        # We keep track of the last time we spoke to avoid overlapping messages
        self.last_spoken_time = 0.0

        # Some variation in positive feedback messages
        self.rep_praise_phrases = [
            "Well done.",
            "That's it.",
            "There you go.",
            "Looks good.",
            "Nice depth.",
            "Form's looking good."
        ]

        # Check if the 'say' command exists on this system (it should on macOS)
        self.has_tts = shutil.which("say") is not None
        if not self.has_tts:
            print("Warning: 'say' command not found. Audio feedback will be disabled.")

    # ---------------------------------------------------------------
    # Internal low-level method for speech
    # ---------------------------------------------------------------
    def _speak(self, text):
        """Internal: run the macOS 'say' command in a blocking way inside a thread."""
        if not self.has_tts:
            return

        try:
            subprocess.call(["say", text])
        except Exception as e:
            print(f"Audio error: {e}")

    # ---------------------------------------------------------------
    # Public non-blocking speech method
    # ---------------------------------------------------------------
    def speak_async(self, text):
        """
        Speak a line of text without blocking the video loop.
        Rate-limited using self.speak_delay.
        """
        if not self.has_tts:
            return

        current_time = time.time()
        # Only speak if enough time has passed
        if current_time - self.last_spoken_time < self.speak_delay:
            return

        self.last_spoken_time = current_time

        thread = threading.Thread(target=self._speak, args=(text,))
        thread.daemon = True
        thread.start()

    # ---------------------------------------------------------------
    # Intro message on the start screen
    # ---------------------------------------------------------------
    def intro_message(self):
        text = (
            "Welcome to the Squat Form Coach. "
            "Stand sideways to the camera, feet hip width apart. "
            "When you're ready, press S to start."
        )
        self.speak_async(text)

    # ---------------------------------------------------------------
    # Main method called every time a REP is counted
    # ---------------------------------------------------------------
    def cheer_for_rep(self, rep_count):
        """
        Called whenever we detect a *valid* squat repetition.

        IMPORTANT:
        ----------
        To avoid the rate limiter blocking secondary messages,
        we build ONE combined message and send it in a single call.
        """
        if not self.has_tts:
            return

        parts = []

        # 1. Basic praise every rep
        parts.append(random.choice(self.rep_praise_phrases))

        # 2. Extra structured feedback
        # a) After every 5th rep, say how many we've done
        if rep_count in (5, 10, 15):
            parts.append(f"That's {rep_count} reps. Nice work.")

        # b) When close to the target, say how many are left
        reps_left = self.target_reps - rep_count
        if reps_left in (10, 5):
            parts.append(f"You have {reps_left} squats left.")

        # c) When done, celebrate
        if rep_count == self.target_reps:
            parts.append("You reached twenty squats. Awesome job. Workout complete.")

        # Build one single spoken message
        full_message = " ".join(parts)

        # Speak it
        self.speak_async(full_message)
