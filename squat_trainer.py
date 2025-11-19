"""
squat_trainer.py

Purpose:
--------
This is the main script that ties everything together:
    - Captures video from the webcam using OpenCV.
    - Uses PoseDetector (pose_module.py) to estimate the user's knee angle.
    - Detects squat repetitions based on knee angle over time.
    - Shows a simple "mini app" interface with a start screen and live overlay.
    - Uses AudioCoach (audio_feedback.py) to give spoken feedback and rep counts.

How the mini-app works:
-----------------------
1. Start the script.
2. A welcome screen appears with instructions (and an optional voice intro).
3. When the user is ready, they stand side-on to the camera and press 'S' to start.
4. The app then tracks squats using a small state machine:
       - "starting": user stands fairly straight (knee angle ~170°+).
       - "descent": knee angle closes while the user moves down.
       - "ascent": when the angle goes below ~90° after a descent, we count one rep.
       - Each valid squat triggers short audio praise + rep info.
5. The app stops automatically when 20 reps are reached, or you can press 'Q' to quit.
"""

import cv2 as cv

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
    cv.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), thickness=-1)
    alpha = 0.6
    frame = cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Title
    cv.putText(frame, "Squat Form Coach",
                (int(0.08 * w), int(0.2 * h)),
                cv.FONT_HERSHEY_SIMPLEX,
                1.3,
                (255, 255, 255),
                3,
                cv.LINE_AA)

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
        cv.putText(frame, line,
                    (int(0.08 * w), y),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv.LINE_AA)
    return frame


def main():
    # --- Configuration parameters ---
    target_reps = 20

    # Create helper objects
    detector = PoseDetector()
    coach = AudioCoach(target_reps=target_reps)

    # Open default webcam
    cap = cv.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # State variables for our simple "state machine"
    started = False          # False = start screen, True = workout running
    rep_count = 0            # current number of completed squats
    stage = "starting"       # stages: "starting" -> "descent" -> "ascent"

    # Optional: play intro once at the beginning
    coach.intro_message()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read from webcam.")
            break

        # Flip horizontally so movement feels more like a mirror
        frame = cv.flip(frame, 1)

        # Start screen until user presses 'S'
        if not started:
            frame = draw_start_screen(frame)
            cv.imshow("Squat Form Coach", frame)

            key = cv.waitKey(30) & 0xFF
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
            cv.circle(frame, knee_point, 8, (0, 255, 255), thickness=-1)

            # Display angle number near knee
            angle_text = f"{int(knee_angle)} deg"
            cv.putText(frame, angle_text,
                        (knee_point[0] + 10, knee_point[1] - 10),
                        cv.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2,
                        cv.LINE_AA)

            # 4. Squat detection logic (state machine inspired by open-source project)
            #
            # Idea:
            # -----
            # We look at how "open" or "closed" the knee angle is and use simple states:
            #   - "starting" : standing fairly straight (big knee angle)
            #   - "descent"  : moving down into the squat
            #   - "ascent"   : coming up from the bottom; we count a rep here
            #
            # This logic is inspired by an open-source fitness pose project (MIT licensed),
            # but implemented here in a simplified way for a single exercise and integrated
            # with our own audio feedback system.

            if knee_angle > 170:
                # Very open angle -> basically standing straight
                stage = "starting"

            elif 90 < knee_angle <= 170 and stage == "starting":
                # Moving down from standing toward a squat
                stage = "descent"

            elif knee_angle <= 90 and stage == "descent":
                # Deep squat reached after a descent -> count one rep
                stage = "ascent"
                rep_count += 1
                coach.cheer_for_rep(rep_count)

        # 5. Draw HUD (Heads-Up Display) with rep counter & status
        h, w, _ = frame.shape

        # Background rectangle for text
        cv.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), thickness=-1)

        # Rep counter
        cv.putText(frame, f"Reps: {rep_count}/{target_reps}",
                    (20, 40),
                    cv.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                    cv.LINE_AA)

        # Stage indicator
        stage_text = f"Stage: {stage.upper()}"
        cv.putText(frame, stage_text,
                    (int(w * 0.5), 40),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (255, 255, 255),
                    2,
                    cv.LINE_AA)

        # Simple hint at the bottom
        cv.putText(frame, "Press 'Q' to quit.",
                    (20, h - 20),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv.LINE_AA)

        cv.imshow("Squat Form Coach", frame)

        # Stop conditions
        key = cv.waitKey(10) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break

        if rep_count >= target_reps:
            # Brief pause to allow final audio to finish
            cv.putText(frame, "Target reached! Great job.",
                        (int(0.1 * w), int(0.5 * h)),
                        cv.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                        cv.LINE_AA)
            cv.imshow("Squat Form Coach", frame)
            cv.waitKey(2000)
            break

    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
