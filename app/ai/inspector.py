# app/ai/inspector.py

import os
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

RETRIES_PER_MODEL = 2
RETRY_DELAY = 2


# ---------------------------------------------------------
# STRUCTURED OUTPUT
# ---------------------------------------------------------

class RoadContext(BaseModel):
    importance_level: Literal["low", "medium", "high"]

    connectivity: dict[str, bool]


class RoadAssessment(BaseModel):
    overall_condition: Literal["good", "fair", "poor", "critical"]
    severity: Literal["low", "moderate", "high", "critical"]
    confidence: Literal["low", "moderate", "high"]

    observed_deterioration: list[str]
    additional_visual_findings: list[str]
    safety_concerns: list[str]

    recommended_action: str
    needs_additional_images: bool

    reasoning: str


# ---------------------------------------------------------
# GEMINI CALL WITH RETRY + FALLBACK
# ---------------------------------------------------------

def _generate(prompt, contents, response_schema):

    last_error = None

    for model in MODELS:

        for attempt in range(RETRIES_PER_MODEL):

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )

                return response.parsed

            except Exception as e:
                last_error = e

                if attempt < RETRIES_PER_MODEL - 1:
                    time.sleep(RETRY_DELAY)

        print(f"Gemini model failed: {model}")

    raise RuntimeError(
        f"All Gemini models failed: {last_error}"
    )


# ---------------------------------------------------------
# ROAD METADATA / CONNECTIVITY ANALYSIS
# ---------------------------------------------------------

def classify_road_context(project_data: dict) -> dict:

    prompt = """
You are a road infrastructure planning assistant working for a
Public Works Department.

Analyze the provided road/project metadata and normalize it into
structured categories.

Do NOT calculate a priority score.
Do NOT estimate road damage.
Do NOT invent information.

Extract only what can reasonably be inferred from the provided
metadata.

Connectivity categories:

- hospital: road provides access to a hospital or major healthcare facility
- school: road provides access to a school
- college: road provides access to a college/university
- commercial: road provides access to markets, commercial areas or major business areas
- daily_commute: road is used for regular residential/work/college travel
- multiple_important_connections: true when the road serves multiple important
  destinations or functions

Importance should be normalized as low, medium or high.
"""

    contents = [
        prompt,
        f"""
Road name: {project_data.get("road_name")}
Location: {project_data.get("location")}
Road type: {project_data.get("road_type")}
Importance: {project_data.get("importance")}
Importance details: {project_data.get("importance_details")}
Connectivity: {project_data.get("connectivity")}
Traffic level: {project_data.get("traffic_level")}
""",
    ]

    result = _generate(
        prompt,
        contents,
        RoadContext,
    )

    return result.model_dump()


# ---------------------------------------------------------
# ROAD IMAGE INSPECTION
# ---------------------------------------------------------

def inspect_road_image(
    image_path: str,
    project_data: dict,
    yolo_result: dict,
) -> dict:

    image_bytes = Path(image_path).read_bytes()

    prompt = """
You are an AI road inspector assisting a Public Works Department engineer.

Inspect the road image as a civil/infrastructure inspection assistant.

Use BOTH:
1. The visual evidence in the image.
2. The YOLO detection evidence provided below.

YOLO detections are supporting evidence, not ground truth.
YOLO confidence represents detection confidence, NOT damage severity.

Assess the visible pavement condition conservatively.

Important rules:
- Do not invent defects that are not visually supported.
- Do not assume a road is good simply because YOLO detected nothing.
- Distinguish between overall road condition and detection confidence.
- Consider visible cracks, potholes, surface deterioration, deformation,
  damaged pavement and other obvious safety-related conditions.
- If the image is insufficient to confidently assess the road, set
  needs_additional_images to true.
- Do not calculate the final Priority Index.
- Do not assign a ranking.
- Do not use road importance/connectivity to exaggerate physical damage.
  Those factors are handled separately by the scoring system.

Return only the requested structured assessment.
"""

    yolo_summary = f"""
YOLO evidence:
Class counts: {yolo_result.get("class_counts", {})}
Pothole count: {yolo_result.get("pothole_count", 0)}
Highest pothole confidence: {yolo_result.get("pothole_top_confidence", 0)}
Top-3 pothole average confidence:
{yolo_result.get("pothole_top_3_avg_confidence", 0)}
"""

    project_context = f"""
Road context:
Road name: {project_data.get("road_name")}
Road type: {project_data.get("road_type")}
Traffic level: {project_data.get("traffic_level")}
"""

    contents = [
        prompt,
        project_context,
        yolo_summary,
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg",
        ),
    ]

    result = _generate(
        prompt,
        contents,
        RoadAssessment,
    )

    return result.model_dump()