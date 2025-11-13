from ultralytics import YOLO

model = YOLO("yolo11n-pose.pt")  # Load model

results = model(source=0, show=True, conf=0.3, save=False)  # Webcam

