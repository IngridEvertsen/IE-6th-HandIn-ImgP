"""
audio_feedback.py

Defines the AudioCoach class, which handles all spoken feedback
for the Squat Form Coach mini-app.

It uses macOS' built-in 'say' command so we don't need extra
Python text-to-speech libraries.

Main responsibilities:
- Play a short spoken intro on startup.
- Cheer when a rep is completed.
- Give small progress updates at certain rep counts.
- Say a final message when the workout is finished.
"""

import threading            # for background audio playback
import random               # for varied praise phrases
import time                 # for timing between spoken lines
import subprocess           # for calling the 'say' command
import shutil               # for checking if 'say' command exists

#----------------------------------------------------------
# AUDIO COACH CLASS (spoken feedback handler)
#----------------------------------------------------------
class AudioCoach:
    
    def __init__(self, target_reps: int = 20, speak_delay: float = 0.7):
        """
        :param target_reps: How many reps the user should reach in total.
        :param speak_delay: Minimum time gap (in seconds) between spoken lines, prevents overlapping / spam.
        """
        self.target_reps = target_reps
        self.speak_delay = speak_delay
        self.last_spoken_time = 0.0

        # A small list of positive phrases to keep feedback varied.
        self.rep_praise_phrases = [
            "Well done.",
            "That's it.",
            "There you go.",
            "Looks good.",
            "Nice depth.",
            "Form's looking good.",
        ]

        # Check if the 'say' command exists on this system (macOS).
        self.has_tts = shutil.which("say") is not None
        if not self.has_tts:
            print("Warning: 'say' command not found.")

    # Internal helpers
    def _speak(self, text: str):
        if not self.has_tts:
            return

        try:
            subprocess.call(["say", text])
        except Exception as e:
            print(f"Audio error: {e}")

    # Public methods that can be called from the main
    def speak_async(self, text: str):
        """
        Speak a line of text without blocking the video loop.

        - Uses a background thread so OpenCV can keep updating the camera.
        - Uses self.speak_delay so lines don't overlap too much.
        """
        if not self.has_tts:
            return

        now = time.time()
        if now - self.last_spoken_time < self.speak_delay:
            # Too soon since the last message -> skip this one
            return

        self.last_spoken_time = now

        thread = threading.Thread(target=self._speak, args=(text,))
        thread.daemon = True 
        thread.start()

    # ----------------------------------------------------------
    # PUBLIC METHODS FOR AUDIO FEEDBACK (called from squat_trainer.py)
    # ----------------------------------------------------------
    def intro_message(self):
        text = (
            "Welcome to the Squat Form Coach. "
            "Stand sideways to the camera, feet hip width apart. "
            "When you're ready, press S to start."
        )
        self.speak_async(text)

    def cheer_for_rep(self, rep_count: int):
        """
        Called whenever we detect a *valid* squat repetition.

        Builds one short sentence combining:
        - a praise phrase
        - optional progress info (e.g. '5 reps', '10 squats left').
        """
        if not self.has_tts:
            return

        parts = []

        # 1) Basic praise every rep
        parts.append(random.choice(self.rep_praise_phrases))

        # 2) At certain rep numbers, say how many we've done
        if rep_count in (5, 10, 15):
            parts.append(f"That's {rep_count} reps.")

        # 3) If close to the goal, mention how many are left
        reps_left = self.target_reps - rep_count
        if reps_left in (10, 5):
            parts.append(f"{reps_left} squats left.")

        # Final combined message for this rep
        full_message = " ".join(parts)
        self.speak_async(full_message)

    def finish_message(self):
        """
        Spoken line when the user reaches the target number of reps.
        Called once from squat_trainer.py at the end of the workout.
        """
        self.speak_async("Target reached. Amazing work. Workout complete.")
