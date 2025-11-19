"""
pose_module.py

Purpose:
--------
This script wraps MediaPipe's Pose module in a small helper class (PoseDetector).
It does three main things:
    1. Detects the body pose in each video frame.
    2. Gives you easy access to landmark coordinates (e.g. hip, knee, ankle).
    3. Calculates the knee angle so we can decide when a squat is "deep enough".

We put this in its own file to:
    - Keep the code in main.py less cluttered.
    - Make it easier to re-use pose detection for other exercises later.
"""

import cv2 as cv
import mediapipe as mp
import numpy as np


class PoseDetector:
    """
    Simple wrapper around MediaPipe Pose.

    Typical usage inside a video loop:
        detector = PoseDetector()
        frame = detector.find_pose(frame)
        angle, knee_point = detector.get_knee_angle(frame, side='left')
    """

    def __init__(self,
                 static_image_mode=False,
                 model_complexity=1,
                 enable_segmentation=False,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5):
        # Store Pose configuration
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # Helper for drawing landmarks and skeleton
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        # This will hold pose results after calling find_pose()
        self.results = None

    def find_pose(self, frame, draw=True):
        """
        Runs pose detection on the given BGR frame (OpenCV format).

        Parameters
        ----------
        frame : np.ndarray
            Input image from webcam (BGR).
        draw : bool
            If True, draw the pose skeleton on the frame.

        Returns
        -------
        frame : np.ndarray
            The same frame, optionally with landmarks drawn.
        """
        # MediaPipe expects RGB images
        img_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        # Run pose estimation
        self.results = self.pose.process(img_rgb)

        # Draw skeleton on the original BGR frame if we have landmarks
        if self.results.pose_landmarks and draw:
            self.mp_drawing.draw_landmarks(
                frame,
                self.results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )

        return frame

    def _landmark_to_pixel(self, frame, landmark):
        """
        Convert a single landmark (x,y in [0,1]) to pixel coordinates.
        """
        h, w, _ = frame.shape
        x_px = int(landmark.x * w)
        y_px = int(landmark.y * h)
        return x_px, y_px

    def get_knee_angle(self, frame, side='left'):
        """
        Calculates the angle at the knee (hip-knee-ankle) for the chosen side.

        side : 'left' or 'right'
            We assume the exerciser stands side-on to the camera, so one leg
            is clearly visible. For this project we expect left side facing the camera.

        Returns
        -------
        angle_degrees : float or None
            The knee angle in degrees, or None if landmarks are missing.
        knee_point : (int, int) or None
            Pixel coordinates of the knee for drawing purposes.
        """
        if self.results is None or self.results.pose_landmarks is None:
            return None, None

        lm = self.results.pose_landmarks.landmark

        # MediaPipe landmark indices for hips / knees / ankles:
        if side.lower() == 'left':
            hip_idx, knee_idx, ankle_idx = 23, 25, 27
        else:
            hip_idx, knee_idx, ankle_idx = 24, 26, 28

        try:
            hip_lm = lm[hip_idx]
            knee_lm = lm[knee_idx]
            ankle_lm = lm[ankle_idx]
        except IndexError:
            # Should not normally happen, but we guard against it
            return None, None

        # Convert normalized coordinates to pixel positions
        hip = np.array(self._landmark_to_pixel(frame, hip_lm))
        knee = np.array(self._landmark_to_pixel(frame, knee_lm))
        ankle = np.array(self._landmark_to_pixel(frame, ankle_lm))

        """
        Calculate the angle at the knee using vector math:

        Vector 1: from knee to hip
        Vector 2: from knee to ankle

        Then we use the cosine rule / dot product to find the angle between them.
        """

        v1 = hip - knee
        v2 = ankle - knee

        # Protect against division by zero
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)
        if v1_norm == 0 or v2_norm == 0:
            return None, tuple(knee.tolist())

        dot_product = np.dot(v1, v2)
        cos_angle = dot_product / (v1_norm * v2_norm)

        # Numerical errors can push cos_angle slightly outside [-1, 1]
        cos_angle = np.clip(cos_angle, -1.0, 1.0)

        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)

        return float(angle_deg), tuple(knee.tolist())
