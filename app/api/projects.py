# app/api/projects.py

import json
import shutil
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

#from app.ai.inspector import classify_road_context
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


class ProjectCreate(BaseModel):
    road_name: str
    location: str = ""
    road_type: str = ""
    length_km: float | None = None
    importance: str = ""
    importance_details: str = ""
    connectivity: str = ""
    traffic_level: str = ""


@router.post("/")
def create_project(project_data: ProjectCreate):

    data = load_data()

    project = {
        "id": f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        **project_data.model_dump(),
        "created_at": date.today().isoformat(),
        "ai_context": {},
        "summary": {
            "priority_index": None,
            "ranking": None,
            "urgency": None
        },
        "inspections": []
    }

    #project["ai_context"] = classify_road_context(project)

    data["projects"].append(project)
    save_data(data)

    return project


@router.put("/{project_id}")
def update_project(project_id: str, project_data: ProjectCreate):

    data = load_data()

    project = next(
        (p for p in data["projects"] if p["id"] == project_id),
        None
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.update(project_data.model_dump())

    # Re-normalize connectivity/importance after metadata changes
    #project["ai_context"] = classify_road_context(project)

    save_data(data)

    return project


@router.delete("/{project_id}")
def delete_project(project_id: str):

    data = load_data()

    project = next(
        (p for p in data["projects"] if p["id"] == project_id),
        None
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data["projects"].remove(project)

    project_dir = UPLOAD_DIR / project_id

    if project_dir.exists():
        shutil.rmtree(project_dir)

    save_data(data)

    return {"message": "Project deleted"}


@router.delete("/{project_id}/inspections/{inspection_id}")
def delete_inspection(project_id: str, inspection_id: str):

    data = load_data()

    project = next(
        (p for p in data["projects"] if p["id"] == project_id),
        None
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    inspection = next(
        (i for i in project["inspections"] if i["id"] == inspection_id),
        None
    )

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    project["inspections"].remove(inspection)

    # Recalculate current summary from the new latest inspection
    result = calculate_priority(project)

    project["summary"]["priority_index"] = result["priority_index"]
    project["summary"]["urgency"] = result["urgency"]

    inspection_dir = UPLOAD_DIR / project_id / inspection_id

    if inspection_dir.exists():
        shutil.rmtree(inspection_dir)

    save_data(data)

    return {
        "message": "Inspection deleted",
        "summary": project["summary"]
    }


@router.get("/")
def get_projects():

    data = load_data()

    projects = data.get("projects", [])

    ranked = sorted(
        projects,
        key=lambda p: p.get("summary", {}).get("priority_index") or 0,
        reverse=True
    )

    for rank, project in enumerate(ranked, start=1):

        priority = project.get("summary", {}).get("priority_index")

        project["summary"]["ranking"] = (
            rank if priority is not None else None
        )

    save_data(data)

    return ranked


@router.get("/{project_id}")
def get_project(project_id: str):

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

    return project