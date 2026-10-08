from ultralytics import YOLO

model = YOLO("backend/models/YOLOv8_Small_RDD.pt")

results = model(
    "uploads/test4.jpeg",
    conf=0.15,
    imgsz=640,
    save=True
)

for result in results:
    print("Detections:", len(result.boxes))

    for box in result.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        print(
            result.names[cls],
            round(conf, 3),
            box.xyxy[0].tolist()
        )

