"""
WHAT THIS SCRIPT DOES:
--------------------------------------------------------------------------------------
- Acts as the CLI entry point that wires the detector, exercise logic, HUD, and audio.
- Parses command-line switches for camera index, YOLO model path, device, and thresholds.
- Starts the webcam loop, runs pose detection, and feeds landmarks into the squat counter.
- Announces completed reps aloud and paints the on-screen HUD for visual confirmation.
--------------------------------------------------------------------------------------
"""
from __future__ import annotations
import argparse
import cv2
from .exercise_logic import SquatCounter
from .pose_detection import PoseDetector
from .sound_feedback import SoundFeedback
from .ui_overlay import UIOverlay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fitness Helper Demo")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--model", type=str, default="yolov8n-pose.pt", help="YOLO pose model path")
    parser.add_argument("--device", type=str, default=None, help="Torch device id (cpu/cuda:0)")
    parser.add_argument("--side", choices=["left", "right"], default="left", help="Body side to track")
    parser.add_argument("--down", type=float, default=70.0, help="Angle threshold for squat bottom")
    parser.add_argument("--up", type=float, default=160.0, help="Angle threshold for squat top")
    parser.add_argument("--no-audio", action="store_true", help="Disable spoken feedback")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open camera index {args.camera}")

    detector = PoseDetector(model_path=args.model, device=args.device)
    counter = SquatCounter(side=args.side, down_angle=args.down, up_angle=args.up)
    sound = SoundFeedback(enabled=not args.no_audio)
    overlay = UIOverlay()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Main] Failed to read frame from camera.")
                break

            annotated, landmarks = detector.detect(frame)

            event = None
            if landmarks is not None:
                event = counter.update(landmarks)
                if event.rep_completed:
                    sound.announce_repetition(counter.rep_count)

            angle = event.angle if event is not None else None
            state = event.state if event is not None else counter.state
            completed = event.rep_completed if event is not None else False
            overlay.draw_hud(annotated, counter.rep_count, angle, state, completed)

            cv2.imshow(overlay.window_name, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
