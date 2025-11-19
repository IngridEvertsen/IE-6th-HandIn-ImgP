"""
WHAT THIS SCRIPT DOES:
--------------------------------------------------------------------------------------
- Uses the Ultralytics YOLO pose weights (trained on the COCO dataset) to locate human
  body landmarks/key points.
  
- Draws a "skeleton" on each video frame by connecting those landmarks so it is easy to
  understand how the detector sees your posture.
  
- Calculates the workout-specific angles we care about, such as:
  - SQUATS: knee angle (squat depth) and back angle (torso straightness).
  - PUSH-UPS: elbow and shoulder angles so we can evaluate form and rep quality.
--------------------------------------------------------------------------------------
"""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Dict, Optional, Sequence, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

Landmark = Tuple[float, float]
LandmarkMap = Dict[str, Landmark]

# COCO keypoint ordering used by YOLO pose models
KEYPOINT_NAMES: Sequence[str] = 
(
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

KEYPOINT_INDEX = {name: idx for idx, name in enumerate(KEYPOINT_NAMES)}

SKELETON_EDGES: Sequence[Tuple[str, str]] = 
(
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
)


@dataclass
class PoseDetectionConfig:
    """
    
    Simple container for the values needed to run the detector.

    Attributes
    ----------
    model_path:
        File name of the YOLO pose weights.  The default points to the compact
        `yolo11n-pose.pt` checkpoint which is lightweight enough for laptops.
    device:
        Optional PyTorch device string (e.g. "cpu", "cuda", "cuda:0").  Leaving it as
        ``None`` lets Ultralytics figure out the best device automatically.
    conf_threshold:
        Minimum confidence value used both by YOLO and our drawing code to ignore very
        uncertain predictions.
    """

    model_path: str = "yolo11n-pose.pt"
    device: Optional[str] = None
    conf_threshold: float = 0.25


class PoseDetector:
    """
    Thin wrapper around Ultralytics YOLO pose models.

    Keeping this logic inside its own class lets the rest of the codebase import the
    detector without repeating all the boilerplate for loading the model and parsing its
    outputs.
    """

    def __init__
    (
        self,
        config: PoseDetectionConfig | None = None,
        *,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        conf_threshold: Optional[float] = None,
    ) -> None:
        # Store the configuration (or create a default one) so we know which weights and
        # device to use at inference time. ``model_path``/``device`` keyword overrides make
        # it easy for callers (e.g., ``main.py``) to customize detection without manually
        # constructing a config object.
        base_config = config or PoseDetectionConfig()
        if model_path is not None:
            base_config = replace(base_config, model_path=model_path)
        if device is not None:
            base_config = replace(base_config, device=device)
        if conf_threshold is not None:
            base_config = replace(base_config, conf_threshold=conf_threshold)
        self.config = base_config
        try:
            # "YOLO(...)" eagerly loads the weights from disk.  We wrap it in "try" so
            # we can show a friendly error message when the file is missing instead of
            # letting the less readable default exception reach the user.
            self.model = YOLO(self.config.model_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError
            (
                "Unable to initialize PoseDetector because the model weights are missing."
            ) from exc

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, Optional[LandmarkMap]]:
        """
        Run inference on a frame and return keypoint coordinates and confidences.

        The Ultralytics ``YOLO`` class returns a list of ``Result`` objects.  Each result
        bundles the data for every pose it sees in the frame.  We loop through the list
        and unpack the tensors into plain Python lists to make downstream usage easier.
        """

        if frame is None:
            raise ValueError("Input frame cannot be None.")

        annotated = frame.copy()
        # ``self.model`` behaves like a callable and accepts numpy arrays (OpenCV images).
        results = self.model
        (
            frame,
            device=self.config.device,
            conf=self.config.conf_threshold,
            verbose=False,
        )

        best_landmarks: Optional[LandmarkMap] = None
        best_score = -np.inf

        for result in results:
            if result.keypoints is None:
                continue

            keypoints_xy = result.keypoints.xy.cpu().numpy()
            confidences = (
                result.keypoints.conf.cpu().numpy()
                if result.keypoints.conf is not None
                else np.ones_like(keypoints_xy[..., 0])
            )

            for instance_xy, instance_conf in zip(keypoints_xy, confidences):
                self._draw_pose(annotated, instance_xy, instance_conf)
                avg_conf = float(np.mean(instance_conf))
                if avg_conf > best_score:
                    best_score = avg_conf
                    best_landmarks = self._name_landmarks(instance_xy)

        return annotated, best_landmarks

    def _name_landmarks(self, keypoints: np.ndarray) -> LandmarkMap:
        return 
        {
            name: (float(coord[0]), float(coord[1]))
            for name, coord in zip(KEYPOINT_NAMES, keypoints)
        }

    def _draw_pose
    (
        self,
        frame: np.ndarray,
        keypoints: np.ndarray,
        confidences: np.ndarray,
    ) -> None:
        conf_thresh = self.config.conf_threshold
        for (name_a, name_b) in SKELETON_EDGES:
            idx_a = KEYPOINT_INDEX[name_a]
            idx_b = KEYPOINT_INDEX[name_b]
            if confidences[idx_a] < conf_thresh or confidences[idx_b] < conf_thresh:
                continue
            pt_a = tuple(map(int, keypoints[idx_a]))
            pt_b = tuple(map(int, keypoints[idx_b]))
            cv2.line(frame, pt_a, pt_b, (0, 255, 0), 2)

        for idx, point in enumerate(keypoints):
            if confidences[idx] < conf_thresh:
                continue
            center = tuple(map(int, point))
            cv2.circle(frame, center, 4, (0, 255, 255), -1)


def body_fully_visible
(
    landmarks: LandmarkMap,
    frame_shape: Tuple[int, int, int],
    *,
    margin: int = 25,
) -> bool:
    """Return ``True`` when every detected landmark sits well inside the frame."""

    if not landmarks:
        return False

    height, width = frame_shape[:2]
    xs = [pt[0] for pt in landmarks.values()]
    ys = [pt[1] for pt in landmarks.values()]

    return 
    (
        min(xs) >= margin
        and min(ys) >= margin
        and max(xs) <= (width - margin)
        and max(ys) <= (height - margin)
    )


__all__ = ["PoseDetector", "PoseDetectionConfig", "body_fully_visible"]

