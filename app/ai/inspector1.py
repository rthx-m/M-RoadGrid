import os
import time
import json
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


PRIMARY_MODEL = "gemini-3.8-flash"

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 2


class RoadAssessment(BaseModel):
    overall_condition: Literal[
        "good",
        "fair",
        "poor",
        "critical"
    ]

    severity: Literal[
        "low",
        "moderate",
        "high",
        "critical"
    ]

    observed_deterioration: list[str]

    yolo_supported_findings: list[str]

    additional_visual_findings: list[str]

    safety_concerns: list[str]

    recommended_action: str

    needs_additional_images: bool

    confidence: Literal[
        "low",
        "moderate",
        "high"
    ]

    reasoning: str



def _generate_with_fallback(image_part, prompt):
    """
    Call Gemini with retry + model fallback.

    Order:
        1. Gemini 3.8 Flash
        2. Retry Gemini 3.8 Flash
        3. Gemini 3.7 Flash
        4. Retry Gemini 3.7 Flash
        5. Gemini 3.6 Flash
        6. Retry Gemini 3.6 Flash
    """

    models = [PRIMARY_MODEL] + FALLBACK_MODELS

    last_error = None

    for model_name in models:

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):

            try:

                print(
                    f"[Gemini] Trying {model_name} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        image_part,
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RoadAssessment,
                    ),
                )

                print(f"[Gemini] Success: {model_name}")

                return response, model_name

            except Exception as e:

                last_error = e

                print(
                    f"[Gemini] {model_name} failed "
                    f"(attempt {attempt}): {e}"
                )

                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(RETRY_DELAY_SECONDS)

        print(
            f"[Gemini] Switching from {model_name} "
            f"to fallback model..."
        )

    raise RuntimeError(
        "All Gemini inspection models failed. "
        f"Last error: {last_error}"
    )


def inspect_road(
    image_path: str,
    yolo_detections: list[dict],
    road_data: dict | None = None
) -> RoadAssessment:

    image_path = Path(image_path)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    road_data = road_data or {}

    prompt = f"""
You are an AI-assisted road inspection engineer working for a
Public Works Department (PWD).

Your job is to inspect the provided road photograph and produce a
careful engineering-oriented visual assessment.

IMPORTANT RULES:

1. Inspect the actual image yourself.
2. Use the YOLO detections as supporting computer-vision evidence,
   but do NOT blindly trust them.
3. You may identify visible deterioration that YOLO did not detect.
4. Do NOT invent exact measurements such as pothole depth, width,
   road roughness, or structural damage when the image does not
   provide enough evidence.
5. Clearly distinguish visible evidence from inference.
6. If the image is insufficient for reliable assessment, say so.
7. Do not claim that the road is safe merely because YOLO detected
   no defects.
8. Assess the visible pavement condition, not the surrounding
   buildings or vehicles.
9. Your output will be used as decision-support, not as a substitute
   for an on-site engineering inspection.

ROAD INFORMATION:

{json.dumps(road_data, indent=2)}

YOLO DETECTIONS:

{json.dumps(yolo_detections, indent=2)}

Assess:

- overall road condition
- visible deterioration
- whether YOLO findings are supported by the image
- important deterioration YOLO may have missed
- safety concerns visible in the image
- whether another image/inspection is needed
- recommended next action

Return only the requested structured assessment.
"""

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=_get_mime_type(image_path)
    )

    response, model_used = _generate_with_fallback(
        image_part,
        prompt
        )

    if response.parsed:
        result = response.parsed
    else:
        result = RoadAssessment.model_validate_json(response.text)

    print(f"[Gemini] Inspector completed using {model_used}")

    return result


def _get_mime_type(path: Path) -> str:

    suffix = path.suffix.lower()

    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    raise ValueError(f"Unsupported image format: {suffix}")

'''
if __name__ == "__main__":

    detections = [
        {
            "class": "Potholes",
            "confidence": 0.74,
            "bbox": [100, 200, 300, 400]
        },
        {
            "class": "Potholes",
            "confidence": 0.57,
            "bbox": [350, 250, 500, 380]
        }
    ]

    road_data = {
        "road_type": "Urban road",
        "traffic_level": "High",
        "road_importance": "High",
        "last_maintenance": "March 2026"
    }

    result = inspect_road(
        "data/uploads/test2.jpeg",
        detections,
        road_data
    )

    print(result.model_dump_json(indent=2)) 

    '''