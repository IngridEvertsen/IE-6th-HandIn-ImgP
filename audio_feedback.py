"""
audio_feedback.py

Purpose:
----------------------------------------------------------------
This script defines a small "AudioCoach" class that handles:
    - Text-to-speech feedback when the user performs good squats.
    - Motivational phrases ("Well done", "Nice depth", etc.).
    - Simple rep counting messages ("That's 5 reps", "10 to go", etc.).

We keep this separate from the main OpenCV loop so:
    - The main code is easier to read.
    - Audio logic can be reused for other exercises or projects.
"""

import threading
import random
import time

import pyttsx3


class AudioCoach:
    """
    Handles all speaking logic using pyttsx3.

    To avoid freezing the video, each message is spoken in a small background thread.
    """

    def __init__(self, target_reps=20, speak_delay=0.7):
        # Create and configure the TTS engine
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 180)   # speaking speed
        self.engine.setProperty("volume", 1.0)  # max volume

        self.target_reps = target_reps
        self.speak_delay = speak_delay  # short pause so we don't spam too fast

        # We keep track of the last time we spoke to avoid overlapping messages
        self.last_spoken_time = 0.0

        # Some variation in positive feedback messages
        self.rep_praise_phrases = 
        [
            "Well done.",
            "That's it.",
            "There you go.",
            "Looks good.",
            "Nice depth.",
            "Form's looking good."
        ]

    def _speak(self, text):
        """
        Internal method that actually runs the speech.
        This is executed in a separate thread.
        """
        self.engine.say(text)
        self.engine.runAndWait()

    def speak_async(self, text):
        """
        Public method to speak without blocking the main video loop.
        """
        current_time = time.time()
        # Only speak if a bit of time has passed since the last message
        if current_time - self.last_spoken_time < self.speak_delay:
            return

        self.last_spoken_time = current_time

        thread = threading.Thread(target=self._speak, args=(text,))
        thread.daemon = True  # if program exits, thread will not block exit
        thread.start()

    def intro_message(self):
        """
        Short welcome instruction that can be played on the start screen.
        """
        text = ("Welcome to the Squat Form Coach. "
                "Stand sideways to the camera, feet hip width apart. "
                "When you're ready, press S to start.")
        self.speak_async(text)

    def cheer_for_rep(self, rep_count):
        """
        Called whenever we detect a *valid* squat repetition.

        It does two things:
          1. Plays a short random praise line.
          2. Sometimes adds extra info like "That's five reps" or "Five to go".
        """
        # 1. Basic praise every rep
        phrase = random.choice(self.rep_praise_phrases)
        self.speak_async(phrase)

        # 2. Additional structured feedback
        #    a) After every 5th rep, say how many we've done
        if rep_count in (5, 10, 15):
            self.speak_async(f"That's {rep_count} reps. Nice work.")

        #    b) When close to the target, say how many are left
        reps_left = self.target_reps - rep_count
        if reps_left in (10, 5):
            self.speak_async(f"You have {reps_left} squats left.")

        #    c) When done, celebrate
        if rep_count == self.target_reps:
            self.speak_async("You reached twenty squats. Awesome job. Workout complete.")

