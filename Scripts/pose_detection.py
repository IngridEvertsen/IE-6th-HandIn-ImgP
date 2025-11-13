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

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from ultralytics import YOLO


@dataclass
class PoseDetectionConfig:
    """Simple container for the values needed to run the detector.

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
    """Thin wrapper around Ultralytics YOLO pose models.

    Keeping this logic inside its own class lets the rest of the codebase import the
    detector without repeating all the boilerplate for loading the model and parsing its
    outputs.
    """

    def __init__(self, config: PoseDetectionConfig | None = None) -> None:
        # Store the configuration (or create a default one) so we know which weights and
        # device to use at inference time.
        self.config = config or PoseDetectionConfig()
        try:
            # ``YOLO(...)`` eagerly loads the weights from disk.  We wrap it in ``try`` so
            # we can show a friendly error message when the file is missing instead of
            # letting the less readable default exception reach the user.
            self.model = YOLO(self.config.model_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "Unable to initialize PoseDetector because the model weights are missing."
            ) from exc

    def detect(self, frame: np.ndarray) -> List[dict]:
        """Run inference on a frame and return keypoint coordinates and confidences.

        The Ultralytics ``YOLO`` class returns a list of ``Result`` objects.  Each result
        bundles the data for every pose it sees in the frame.  We loop through the list
        and unpack the tensors into plain Python lists to make downstream usage easier.
        """

        if frame is None:
            raise ValueError("Input frame cannot be None.")

        # ``self.model`` behaves like a regular callable and accepts numpy arrays
        # (OpenCV images).  ``verbose=False`` avoids spamming progress bars during the
        # webcam loop.
        results = self.model(
            frame,
            device=self.config.device,
            conf=self.config.conf_threshold,
            verbose=False,
        )

        detections: List[dict] = []
        for result in results:
            if result.keypoints is None:
                continue

            # ``keypoints`` is a tensor shaped ``(poses, num_keypoints, 2)`` with ``x``
            # and ``y`` coordinates.  ``.xy`` converts it to pixel locations relative to
            # the input image size.
            keypoints_xy = result.keypoints.xy.cpu().numpy()
            confidences = (
                result.keypoints.conf.cpu().numpy()
                if result.keypoints.conf is not None
                else np.ones_like(keypoints_xy[..., 0])
            )

            for instance_xy, instance_conf in zip(keypoints_xy, confidences):
                # We convert the numpy arrays to plain lists so that they are trivial to
                # serialize or print for debugging.
                detections.append(
                    {
                        "keypoints": instance_xy.tolist(),
                        "confidences": instance_conf.tolist(),
                    }
                )

        return detections


__all__ = ["PoseDetector", "PoseDetectionConfig"]
