# IE-6th-HandIn-ImgP Repository
Mini Project for the course "Image Processing", from the third semester of the Medialogy Bachelor at Aalborg University - Campus Copenhagen.

# Fitness Helper Demo
This repository contains a modular fitness helper prototype built with OpenCV and
Ultralytics YOLO pose estimation. The app monitors a user's movement through
webcam input and provides visual + spoken feedback for common exercises such as
squats and push-ups at this point, however with the possibility to upscale with added exercises later on.

# Instructions 


PS!!
Exerciser should wear fitted clothing to that the model more easily and accurately measure the pose/anchor points.


# Demo Video
Link: #will be uploaded once done and recorded


# Squat Form Coach 🏋️‍♀️

A small computer-vision based fitness helper that provides **real-time feedback** on bodyweight squats using **MediaPipe Pose** and **OpenCV**.
The app guides the user through a simple squat exercise, gives spoken positive feedback when reps are detected, and counts towards a target of **20 squats**.


## 1. Project Overview

This mini-app was developed for an assignment requiring:

> *"A simple game or app using OpenCV and another computer vision library (e.g. MediaPipe, Ultralytics, etc.), with code and a short demo video."*


### Main idea

- The user stands **sideways** to the webcam, full body visible.
- The system uses **MediaPipe Pose** to track key body landmarks.
- It computes the **knee angle** (hip–knee–ankle) to understand squat depth.
- A simple **state machine** is used to detect complete squat repetitions.
- When a valid rep is detected:
  - The app **counts the rep**.
  - Gives **spoken praise** (e.g. “Well done”, “Nice depth”).
  - Occasionally informs the user how many reps are done / left.

The experience is wrapped in a small “mini app” UI:
- Start screen with instructions.
- Live overlay with rep count and current stage.


## 2. Files in This Project

- `squat_trainer.py`  
  The **main script**:
  - Opens webcam (OpenCV).
  - Displays the start screen and workout UI.
  - Uses `PoseDetector` to get knee angle.
  - Uses a state machine to detect squat reps.
  - Calls `AudioCoach` to give spoken feedback.

- `pose_module.py`  
  A small helper module that wraps **MediaPipe Pose**:
  - Detects pose landmarks.
  - Converts normalized coordinates to pixels.
  - Computes the **knee angle** using vector math.

- `audio_feedback.py`  
  Handles **audio coaching**:
  - Uses macOS’ built-in `say` command for text-to-speech.
  - Provides short praise lines and rep-count feedback.

- `README.md`  
  This file – documentation and setup instructions.



## 3. Requirements

- **Python**: 3.x (tested on macOS with Python 3)
- **Operating system**: macOS (for the `say` command used for audio)

### Python packages

Inside a virtual environment, install:
```bash
pip install opencv-python
pip install mediapipe
pip install numpy
