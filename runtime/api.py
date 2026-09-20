from __future__ import annotations

import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from brain.config import settings
from brain.engine import brain
from brain.project_manager import project_manager
from brain.schemas import BrainStats, ChatRequest, ChatResponse
from personality.evolution import evolution


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Klyor Brain", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    error_type = type(exc).__name__
    error_message = str(exc) or "No error message was provided."
    trace = traceback.format_exc()

    print("\n===== KLYOR BRAIN ERROR =====")
    print(trace)
    print("===== END KLYOR BRAIN ERROR =====\n")

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "error_type": error_type,
            "message": error_message,
            "traceback": trace,
        },
    )


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health")
async def api_health():
    return {"ok": True, "status": "ok"}


@app.get("/api/status")
async def api_status():
    return evolution.status_summary()


@app.get("/api/evolution")
async def get_evolution():
    return evolution.stats()


@app.post("/api/evolution/run")
async def run_evolution():
    return evolution.evolve()


@app.get("/api/info")
async def info():
    return {
        "name": "Klyor Brain",
        "version": "0.1.0",
        "engine": "local capability engine",
    }


@app.get("/api/project")
async def get_project():
    return project_manager.status()


@app.get("/api/project/context")
async def get_project_context():
    return project_manager.context()


@app.get("/api/project/validation")
async def get_project_validation():
    project = project_manager.current_path()
    if project is None:
        return {"valid": False, "errors": ["no active project"]}
    return project_manager.validate(project)


@app.post("/api/project/reset")
async def reset_project():
    project_manager.reset()
    return {"ok": True, "project": project_manager.status()}


@app.get("/api/project/file")
async def get_project_file(path: str):
    try:
        content = project_manager.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project file not found.")
    return {
        "path": path,
        "content": content,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_messages = [
        message.content.strip()
        for message in request.messages
        if message.role == "user" and message.content.strip()
    ]

    if not user_messages:
        raise HTTPException(
            status_code=400,
            detail="Please enter a message.",
        )

    try:
        result = brain.answer(user_messages[-1], mode=request.mode)

        return ChatResponse(
            message=result.response,
            learned=getattr(result, 'learned', False),
            confidence=result.confidence,
            capability=result.capability,
            project=result.project,
            status=result.status,
        )

    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc) or "No error message was provided."
        trace = traceback.format_exc()

        print("\n===== KLYOR CHAT ERROR =====")
        print(trace)
        print("===== END KLYOR CHAT ERROR =====\n")

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_type": error_type,
                "message": error_message,
                "traceback": trace,
            },
        )


@app.get("/api/stats", response_model=BrainStats)
async def stats():
    return BrainStats(
        training_examples=brain.training_example_count(),
        engine="local capability engine",
    )


@app.get("/preview/")
async def preview_root():
    project = project_manager.status()

    if not project.get("exists"):
        response = FileResponse(STATIC_DIR / "preview-empty.html")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    response = FileResponse(project_manager.project_dir / "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/preview/{path:path}")
async def preview_asset(path: str):
    project = project_manager.status()

    if not project.get("exists"):
        response = FileResponse(STATIC_DIR / "preview-empty.html")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    safe_root = project_manager.project_dir.resolve()
    requested = (safe_root / path).resolve()

    if safe_root not in requested.parents and requested != safe_root:
        raise HTTPException(status_code=403, detail="Invalid preview path.")

    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Preview asset not found.")

    response = FileResponse(requested)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
