from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import projects, inspections

app = FastAPI(title="PWD Road Intelligence")


# API routes
app.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

app.include_router(
    inspections.router,
    prefix="/inspections",
    tags=["Inspections"]
)


# Uploaded road images
app.mount(
    "/uploads",
    StaticFiles(directory="data/uploads"),
    name="uploads"
)


# Frontend assets
app.mount(
    "/css",
    StaticFiles(directory="frontend/css"),
    name="css"
)

app.mount(
    "/js",
    StaticFiles(directory="frontend/js"),
    name="js"
)


# SPA fallback
@app.get("/{path:path}")
async def frontend(path: str):
    return FileResponse("frontend/index.html")