# app/api/analysis.py

from pathlib import Path

from app.ai.yolo import detect_road_damage
from app.ai.inspector import inspect_road_image
from app.assessment.scoring import calculate_priority


def analyze_image(
    project: dict,
    inspection: dict,
    image: dict
) -> dict:

    image_path = image["original_path"]

    yolo_output_dir = str(
        Path(image_path).parent.parent / "yolo"
    )

    # 1. YOLO detection
    yolo_result = detect_road_damage(
        image_path,
        yolo_output_dir
    )

    # Keep only the data needed in road_data.json
    image["yolo"] = {
        "class_counts": yolo_result.get("class_counts", {}),
        "pothole_top_confidence": yolo_result.get(
            "pothole_top_confidence", 0
        ),
        "pothole_top_3_avg_confidence": yolo_result.get(
            "pothole_top_3_avg_confidence", 0
        )
    }

    image["yolo_path"] = yolo_result["annotated_image"]

    # 2. Gemini inspection
    image["ai_inspection"] = inspect_road_image(
        image_path,
        project,
        yolo_result
    )

    # 3. Calculate latest inspection priority
    result = calculate_priority(project)

    project["summary"]["priority_index"] = result["priority_index"]
    project["summary"]["urgency"] = result["urgency"]

    return image