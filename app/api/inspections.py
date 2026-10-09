# app/api/inspections.py

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.api.analysis import analyze_image
from app.assessment.scoring import calculate_priority

router = APIRouter()

DATA_FILE = Path("data/road_data.json")
UPLOAD_DIR = Path("data/uploads")


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)



@router.post("/{project_id}")
async def create_inspection(
    project_id: str,
    date: str = Form(...),
    inspector: str = Form(""),
    last_maintenance_date: str = Form(""),
    maintenance_notes: str = Form(""),
    notes: str = Form(""),
    images: list[UploadFile] = File(...)
):
    data = load_data()

    project = next(
        (p for p in data["projects"] if p["id"] == project_id),
        None
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    inspection_id = f"INSP-{uuid.uuid4().hex[:6].upper()}"

    inspection_dir = UPLOAD_DIR / project_id / inspection_id
    original_dir = inspection_dir / "original"
    yolo_dir = inspection_dir / "yolo"

    original_dir.mkdir(parents=True, exist_ok=True)
    yolo_dir.mkdir(parents=True, exist_ok=True)

    inspection = {
        "id": inspection_id,
        "date": date,
        "inspector": inspector,
        "maintenance": {
            "last_maintenance_date": last_maintenance_date,
            "notes": maintenance_notes
        },
        "notes": notes,
        "images": []
    }

    # 1. Save all uploaded images first
    for upload in images:
        image_id = f"IMG-{uuid.uuid4().hex[:6].upper()}"
        filename = Path(upload.filename).name
        original_path = original_dir / filename

        content = await upload.read()
        original_path.write_bytes(content)

        image = {
            "id": image_id,
            "filename": filename,
            "original_path": str(original_path),
            "yolo_path": "",
            "yolo": {},
            "ai_inspection": {}
        }

        inspection["images"].append(image)

    if not inspection["images"]:
        raise HTTPException(
            status_code=400,
            detail="At least one image is required"
        )

    # 2. Add inspection before running analysis
    project["inspections"].append(inspection)

    # 3. Run YOLO and Gemini for each image
    for image in inspection["images"]:
        analyze_image(project, inspection, image)

    # 4. Calculate priority once, using the completed inspection
    result = calculate_priority(project)

    project["summary"]["priority_index"] = result["priority_index"]
    project["summary"]["urgency"] = result["urgency"]

    # 5. Recalculate rankings for every project
    ranked_projects = sorted(
        data["projects"],
        key=lambda p: (
            p.get("summary", {}).get("priority_index") is not None,
            p.get("summary", {}).get("priority_index") or 0
        ),
        reverse=True
    )

    for project_rank, ranked_project in enumerate(
        ranked_projects, start=1
    ):
        priority = ranked_project.get(
            "summary", {}
        ).get("priority_index")

        ranked_project["summary"]["ranking"] = (
            project_rank if priority is not None else None
        )

    # 6. Persist scores and rankings
    save_data(data)

    return {
        "inspection": inspection,
        "summary": project["summary"]
    }
