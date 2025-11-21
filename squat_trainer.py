"""
squat_trainer.py

Purpose:
--------
This is the main script that ties everything together:
    - Captures video from the webcam using OpenCV.
    - Uses PoseDetector (pose_module.py) to estimate the user's knee angle.
    - Detects squat repetitions based on knee angle over time.
    - Shows a simple "mini app" interface (HUD) with a start screen and live overlay.
    - Uses AudioCoach (audio_feedback.py) to give spoken feedback and rep counts.

How the mini-app works:
-----------------------
1. Start the script.
2. A welcome screen appears with instructions and a voice intro.
3. When the user is ready, they stand side-on to the camera and press 'S' to start.
4. The app then tracks squats using a small state machine:
       - "standing Up": user stands fairly straight (knee angle ~170°+).
       - "Going Down": knee angle closes while the user moves down.
       - "Coming Up": when the angle goes below ~90° after a descent, we count one rep.
       - Valid squats triggers short audio praise + rep info.
5. The app stops automatically when 20 reps are reached, or you can press 'Q' to quit.
"""

import cv2 as cv
import time

from pose_module import PoseDetector        # import our PoseDetector class
from audio_feedback import AudioCoach       # import our AudioCoach class

# UI COLORS (BGR for OpenCV)
# Palette from: #8DBBC2, #4F362A, #6F0D3A
COLOR_HEADER  = (58, 13, 111)        # 6F0D3A cherry wine (used for main header and instructions)
COLOR_SUBHEAD = (194, 187, 141)      # 8DBBC2 soft blue (used for subheaders)
COLOR_VALUE   = (42, 54, 79)         # 4F362A deep brown (rep count + state)


# ----------------------------------------------------------
# START SCREEN DRAWING FUNCTION
# ----------------------------------------------------------
def draw_start_screen(frame):
    """
    Draws a welcome / instruction overlay on top of the live camera feed.
    Styled to match the in-game HUD (heads-up display).
    """
    h, w, _ = frame.shape
    font = cv.FONT_HERSHEY_SIMPLEX

    # HEADER (CENTERED, CHERRY PINK, CAPS)
    header_text = "SQUAT FORM COACH"
    header_scale = 1.6
    header_thickness = 3

    (header_w, header_h), _ = cv.getTextSize(header_text, font, header_scale, header_thickness)
    header_x = (w - header_w) // 2
    header_y = 70

    cv.putText(
        frame,
        header_text,
        (header_x, header_y),
        font,
        header_scale,
        COLOR_HEADER,
        header_thickness,
        cv.LINE_AA
    )

    # LEFT COLUMN: INSTRUCTIONS HEADER
    subheader_text = "WELCOME"
    sub_scale = 0.95
    sub_thick = 2

    start_x = 40
    base_y = 130

    cv.putText(
        frame,
        subheader_text,
        (start_x, base_y),
        font,
        sub_scale,
        COLOR_SUBHEAD,
        sub_thick,
        cv.LINE_AA
    )

    # LEFT COLUMN: INSTRUCTIONS BODY
    lines = [
        "Stand sideways to the camera, full body visible.",
        "Feet hip-width apart, arms free.",
        "Perform bodyweight squats to about 90 degrees.",
        "You will hear feedback when your form is good.",
        "Target: 20 squats."
    ]

    body_scale = 0.75
    body_thick = 2
    line_spacing = 28
    y = base_y + 35

    for line in lines:
        cv.putText(
            frame,
            line,
            (start_x, y),
            font,
            body_scale,
            (255, 255, 255),  # White text
            body_thick,
            cv.LINE_AA
        )
        y += line_spacing

    # CALL TO ACTION (BOTTOM, CHERRY PINK, CAPS)
    bottom_text = "PRESS S TO START    TO QUIT -> PRESS Q"
    bottom_scale = 0.8
    bottom_thick = 2

    (bt_w, bt_h), _ = cv.getTextSize(bottom_text, font, bottom_scale, bottom_thick)
    bt_x = (w - bt_w) // 2
    bt_y = h - 40

    cv.putText(
        frame,
        bottom_text,
        (bt_x, bt_y),
        font,
        bottom_scale,
        COLOR_HEADER,
        bottom_thick,
        cv.LINE_AA
    )

    return frame

# ----------------------------------------------------------
# MAIN APPLICATION LOOP
# ----------------------------------------------------------
def main():
    # Configuration parameters
    target_reps = 20

    # Create helper objects for pose detection and audio feedback
    detector = PoseDetector()
    coach = AudioCoach(target_reps=target_reps)

    # Open default webcam (should be at index 0)
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Create a named window and set it to fullscreen
    window_name = "Squat Form Coach"
    cv.namedWindow(window_name, cv.WINDOW_NORMAL)
    cv.setWindowProperty(window_name, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    # State variables for our simple "state machine"
    started = False          # False = start screen, True = workout running
    rep_count = 0            # current number of completed squats
    stage = "starting"       # stages: "starting" -> "going down" -> "coming up"

    # Play intro once at the beginning, with a small delay so that window has loaded before audio starts
    time.sleep(8)
    coach.intro_message()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read from webcam.")
            break

        # Flip horizontally so movement feels more like a mirror
        frame = cv.flip(frame, 1)

        # ----------------------------------------------------------
        # START SCREEN MODE
        # ----------------------------------------------------------
        if not started:
            frame = draw_start_screen(frame)
            cv.imshow(window_name, frame)

            key = cv.waitKey(30) & 0xFF
            if key in (ord('s'), ord('S')):
                started = True
                coach.speak_async("Starting squat tracking. Let's go.")
            elif key in (ord('q'), ord('Q')):
                break

            continue  # skip rest of loop until started

        # ----------------------------------------------------------
        # WORKOUT MODE 
        # ----------------------------------------------------------
        # 1. Detect pose and draw skeleton
        frame = detector.find_pose(frame, draw=True)

        # 2. Compute knee angle from pose
        knee_angle, knee_point = detector.get_knee_angle(frame, side='left')

        # 3. Visualize the knee angle and update stage/rep count
        if knee_angle is not None:
            # small circle on the knee
            cv.circle(frame, knee_point, 8, (0, 255, 255), thickness=-1)

            # numeric angle label
            angle_text = f"{int(knee_angle)} deg"
            cv.putText(
                frame,
                angle_text,
                (knee_point[0] + 10, knee_point[1] - 10),
                cv.FONT_HERSHEY_SIMPLEX,
                0.7,
                (58, 13, 111),
                2,
                cv.LINE_AA
            )

            # simple squat state machine
            if knee_angle > 170:
                stage = "Standing Up"
            elif 90 < knee_angle <= 170 and stage == "Standing Up":
                stage = "Going Down"
            elif knee_angle <= 90 and stage == "Going Down":
                stage = "Coming Up"
                rep_count += 1
                coach.cheer_for_rep(rep_count)

        # ----------------------------------------------------------
        # HEADS UP DISPLAY (HUD)
        # ---------------------------------------------------------- 
        h, w, _ = frame.shape
        font = cv.FONT_HERSHEY_SIMPLEX

        # Header
        header_text = "SQUAT FORM COACH"
        header_scale = 1.4
        header_thickness = 3
        (header_w, header_h), _ = cv.getTextSize(header_text, font, header_scale, header_thickness)
        header_x = (w - header_w) // 2
        header_y = 60

        cv.putText(
            frame,
            header_text,
            (header_x, header_y),
            font,
            header_scale,
            COLOR_HEADER,
            header_thickness,
            cv.LINE_AA
        )

        # Left/right layout
        left_x = 40
        base_y = 150
        right_margin = 40

        sub_scale = 0.75
        sub_thick = 2
        val_scale = 1.3
        val_thick = 3

        # Left: REP COUNT
        cv.putText(
            frame,
            "REP COUNT",
            (left_x, base_y),
            font,
            sub_scale,
            COLOR_SUBHEAD,
            sub_thick,
            cv.LINE_AA
        )

        rep_text = f"{rep_count}/{target_reps}"
        cv.putText(
            frame,
            rep_text,
            (left_x, base_y + 45),
            font,
            val_scale,
            COLOR_VALUE,
            val_thick,
            cv.LINE_AA
        )

        # Right: STATE (right-aligned)
        state_label = "STATE"
        (label_w, _), _ = cv.getTextSize(state_label, font, sub_scale, sub_thick)
        label_x = w - right_margin - label_w

        cv.putText(
            frame,
            state_label,
            (label_x, base_y),
            font,
            sub_scale,
            COLOR_SUBHEAD,
            sub_thick,
            cv.LINE_AA
        )

        state_text = stage.upper()
        (state_w, _), _ = cv.getTextSize(state_text, font, val_scale, val_thick)
        state_x = w - right_margin - state_w

        cv.putText(
            frame,
            state_text,
            (state_x, base_y + 45),
            font,
            val_scale,
            COLOR_VALUE,
            val_thick,
            cv.LINE_AA
        )

        # Bottom instruction
        hint_text = "TO QUIT -> PRESS Q"
        cv.putText(
            frame,
            hint_text,
            (40, h - 40),
            font,
            0.75,
            COLOR_HEADER,
            2,
            cv.LINE_AA
        )

        # Show frame
        cv.imshow(window_name, frame)

        # ----------------------------------------------------------
        # FINAL PHASE AND KEY HANDLING (quit or finish)
        # ----------------------------------------------------------
        key = cv.waitKey(10) & 0xFF
        if key in (ord('q'), ord('Q')):
            break

        if rep_count >= target_reps:
            # Centered blue "target reached" text
            final_text = "TARGET REACHED, AMAZING WORK!"
            final_scale = 1.2
            final_thick = 3

            # Measure text size so we can center it
            (text_w, text_h), _ = cv.getTextSize(final_text, font, final_scale, final_thick)
            text_x = (w - text_w) // 2
            text_y = h // 2

            # Draw the message
            cv.putText(
                frame,
                final_text,
                (text_x, text_y),
                font,
                final_scale,
                COLOR_SUBHEAD,    
                final_thick,
                cv.LINE_AA
            )

             # Play finishing message
            coach.finish_message()

            # Show the final frame
            cv.imshow(window_name, frame)

            # Keep the window open long enough for the voice to finish
            end_time = time.time() + 5  # keep it up ~5 seconds
            while time.time() < end_time:
                # keep re-showing the same final frame
                cv.imshow(window_name, frame)
                key = cv.waitKey(50) & 0xFF
                if key in (ord('q'), ord('Q')):
                    break

            break

    cap.release()
    cv.destroyAllWindows()

# ----------------------------------------------------------
# ENTRY POINT (calling main() function)
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
