"""
squat_trainer.py

Purpose:
--------
This is the main script that ties everything together:
    - Captures video from the webcam using OpenCV.
    - Uses PoseDetector (pose_module.py) to estimate the user's knee angle.
    - Detects squat repetitions based on knee angle going below/above thresholds.
    - Shows a simple "mini app" interface with a start screen and live overlay.
    - Uses AudioCoach (audio_feedback.py) to give spoken feedback and rep counts.

How the mini-app works:
-----------------------
1. Start the script.
2. A welcome screen appears with instructions (and an optional voice intro).
3. When the user is ready, they stand side-on to the camera and press 'S' to start.
4. The app then tracks squats:
       - When the knee angle goes below ~90°, we consider the user "down".
       - When the angle then goes above ~150° again, we count it as one squat.
       - Each valid squat triggers short audio praise + rep info.
5. The app stops automatically when 20 reps are reached, or you can press 'Q' to quit.
"""

import cv2
import numpy as np

from pose_module import PoseDetector
from audio_feedback import AudioCoach


def draw_start_screen(frame):
    """
    Draws a simple welcome / instruction overlay on top of the live camera feed.
    This makes it feel more like a mini application instead of plain debug output.
    """
    h, w, _ = frame.shape

    # Semi-transparent dark overlay to make text readable
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), thickness=-1)
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Title
    cv2.putText(frame, "Squat Form Coach",
                (int(0.08 * w), int(0.2 * h)),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.3,
                (255, 255, 255),
                3,
                cv2.LINE_AA)

    # Short description
    y0 = int(0.35 * h)
    dy = 30
    instructions = [
        "Stand sideways to the camera, full body visible.",
        "Feet hip-width apart, arms free.",
        "You will perform bodyweight squats.",
        "Go down until your knees are bent to about 90 degrees.",
        "You will hear feedback when your form is good.",
        "Target: 20 squats.",
        "",
        "Press 'S' to start. Press 'Q' to quit."
    ]
    for i, line in enumerate(instructions):
        y = y0 + i * dy
        cv2.putText(frame, line,
                    (int(0.08 * w), y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA)
    return frame


def main():
    # --- Configuration parameters ---
    target_reps = 20
    down_angle_threshold = 90    # below this is considered "deep enough"
    up_angle_threshold = 150     # above this is considered standing

    # Create helper objects
    detector = PoseDetector()
    coach = AudioCoach(target_reps=target_reps)

    # Open default webcam
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # State variables for our simple "state machine"
    started = False      # False = start screen, True = workout running
    rep_count = 0        # current number of completed squats
    stage = "up"         # "up" or "down" to avoid double-counting

    # Optional: play intro once at the beginning
    coach.intro_message()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read from webcam.")
            break

        # Flip horizontally so movement feels more like a mirror
        frame = cv2.flip(frame, 1)

        # Start screen until user presses 'S'
        if not started:
            frame = draw_start_screen(frame)
            cv2.imshow("Squat Form Coach", frame)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('s') or key == ord('S'):
                started = True
                # short audio cue for starting
                coach.speak_async("Starting squat tracking. Let's go.")
            elif key == ord('q') or key == ord('Q'):
                break

            continue  # skip the rest of the loop until started

        # ----- Workout mode -----

        # 1. Detect pose and draw skeleton
        frame = detector.find_pose(frame, draw=True)

        # 2. Compute knee angle from pose
        knee_angle, knee_point = detector.get_knee_angle(frame, side='left')

        # 3. Visualize the knee angle
        if knee_angle is not None:
            # Draw a small circle at the knee
            cv2.circle(frame, knee_point, 8, (0, 255, 255), thickness=-1)

            # Display angle number near knee
            angle_text = f"{int(knee_angle)} deg"
            cv2.putText(frame, angle_text,
                        (knee_point[0] + 10, knee_point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2,
                        cv2.LINE_AA)

            # 4. Squat detection logic (simple state machine)
            #
            # We only want to count ONE rep when the user goes:
            #   "up"  ->  "down" (angle < down_threshold)  ->  "up again"
            #
            # So we:
            #   - Set stage = "down" when angle is low enough.
            #   - Count a rep when angle is high again and stage was "down".
            if knee_angle < down_angle_threshold and stage == "up":
                stage = "down"  # user has gone down far enough

            if knee_angle > up_angle_threshold and stage == "down":
                stage = "up"
                rep_count += 1
                coach.cheer_for_rep(rep_count)

        # 5. Draw HUD (Heads-Up Display) with rep counter & status
        h, w, _ = frame.shape

        # Background rectangle for text
        cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), thickness=-1)

        # Rep counter
        cv2.putText(frame, f"Reps: {rep_count}/{target_reps}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA)

        # Stage indicator
        stage_text = f"Stage: {stage.upper()}"
        cv2.putText(frame, stage_text,
                    (int(w * 0.5), 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA)

        # Simple hint at the bottom
        cv2.putText(frame, "Press 'Q' to quit.",
                    (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA)

        cv2.imshow("Squat Form Coach", frame)

        # Stop conditions
        key = cv2.waitKey(10) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break

        if rep_count >= target_reps:
            # Brief pause to allow final audio to finish
            cv2.putText(frame, "Target reached! Great job.",
                        (int(0.1 * w), int(0.5 * h)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA)
            cv2.imshow("Squat Form Coach", frame)
            cv2.waitKey(2000)
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
