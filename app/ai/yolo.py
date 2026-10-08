from pathlib import Path
import json

import cv2
from ultralytics import YOLO


MODEL_PATH = Path("models/YOLOv8_Small_RDD.pt")

CONF_THRESHOLD = 0.15
IMAGE_SIZE = 640

model = YOLO(str(MODEL_PATH))


def detect_road_damage(
    image_path: str,
    yolo_output_dir: str
) -> dict:

    output_dir = Path(yolo_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = model.predict(
        source=image_path,
        conf=CONF_THRESHOLD,
        imgsz=IMAGE_SIZE,
        verbose=False
    )

    result = results[0]

    detections = []

    if result.boxes is not None:
        for i in range(len(result.boxes)):

            class_id = int(result.boxes.cls[i].item())
            confidence = float(result.boxes.conf[i].item())
            x1, y1, x2, y2 = result.boxes.xyxy[i].tolist()

            detections.append({
                "class": model.names[class_id],
                "confidence": round(confidence, 3),
                "bbox": [
                    round(x1, 1),
                    round(y1, 1),
                    round(x2, 1),
                    round(y2, 1)
                ]
            })

    class_counts = {}

    for d in detections:
        class_counts[d["class"]] = (
            class_counts.get(d["class"], 0) + 1
        )

    pothole_confidences = sorted(
        [
            d["confidence"]
            for d in detections
            if d["class"].lower() == "potholes"
        ],
        reverse=True
    )

    pothole_count = len(pothole_confidences)

    top_pothole_confidence = (
        pothole_confidences[0]
        if pothole_confidences
        else 0.0
    )

    top_3 = pothole_confidences[:3]

    top_3_avg_confidence = round(
        sum(top_3) / len(top_3),
        3
    ) if top_3 else 0.0

    # Generate annotated image
    annotated = result.plot()

    annotated_path = output_dir / Path(image_path).name

    cv2.imwrite(
        str(annotated_path),
        annotated
    )

    return {
        "annotated_image": str(annotated_path),
        "total_detections": len(detections),
        "class_counts": class_counts,
        "pothole_count": pothole_count,
        "pothole_top_confidence": top_pothole_confidence,
        "pothole_top_3_avg_confidence": top_3_avg_confidence,
        "detections": detections
    }


# Temporary test
'''
if __name__ == "__main__":

    result = detect_road_damage(
        "data/uploads/test3.jpeg",
        "data/uploads/project_001/inspection_001/yolo"
    )

    print(json.dumps(result, indent=2))
'''