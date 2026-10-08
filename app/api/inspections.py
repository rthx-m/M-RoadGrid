# app/api/inspections.py

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.api.analysis import analyze_image

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
        raise HTTPException(status_code=404, detail="Project not found")

    inspection_id = f"INSP-{uuid.uuid4().hex[:6].upper()}"

    inspection_dir = (
        UPLOAD_DIR / project_id / inspection_id
    )

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

    # Save images and create image records
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

        # Run YOLO → Gemini → scoring
        analyze_image(
            project,
            inspection,
            image
        )

    # Add inspection to project
    project["inspections"].append(inspection)

    save_data(data)

    return {
        "inspection": inspection,
        "summary": project["summary"]
    }