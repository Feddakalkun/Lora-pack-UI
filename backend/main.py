from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import quote
import glob
import os
import subprocess
import sys

# Services
from services.job_manager import job_manager
from services.downloader_service import downloader_service
from scripts.cookie_store import (
    cookie_file_state,
    load_cookie_config,
    save_cookie_config,
)

app = FastAPI(title="LoRA Pack UI Backend")

BACKEND_ROOT = Path(__file__).resolve().parent
DOWNLOADS_ROOT = BACKEND_ROOT / "downloads"
VSCO_PROFILE_DIR = BACKEND_ROOT / ".auth" / "vsco_playwright_profile"

# Ensure directories exist
DOWNLOADS_ROOT.mkdir(parents=True, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class DownloadRequest(BaseModel):
    url: str
    limit: int | None = None
    platform: str
    character: str = "Unsorted"
    vsco_cookies_file: str | None = None
    tiktok_cookies_file: str | None = None

class CookieConfigRequest(BaseModel):
    vsco: str = ""
    tiktok: str = ""
    instagram: str = ""

class FrameExtractionRequest(BaseModel):
    video_path: str
    character: str
    interval: float = 1.0
    max_frames: int | None = None
    output_subfolder: str = "frames"

# --- Endpoints ---

@app.get("/")
def index():
    return {"status": "ok", "message": "LoRA Pack Backend is purring."}

# --- Download Management ---

@app.post("/api/download/start")
def download_start(req: DownloadRequest):
    job_id = job_manager.create_job(req.url, req.character, req.model_dump())
    
    downloader_service.dispatch_and_run(
        job_id=job_id,
        url=req.url,
        character=req.character,
        vsco_cookies=req.vsco_cookies_file,
        tiktok_cookies=req.tiktok_cookies_file
    )
    
    return {
        "status": "success",
        "job_id": job_id,
        "message": "Download started in background.",
    }

@app.get("/api/download/status/{job_id}")
def download_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        return {"status": "error", "message": "Job not found."}
    return {"status": "success", "job": job}

@app.post("/api/job/update/{job_id}")
def update_job_status(job_id: str, data: Dict[str, Any]):
    job_manager.update_job(
        job_id, 
        status=data.get("status"), 
        progress=data.get("progress"), 
        message=data.get("message"), 
        result=data.get("result")
    )
    return {"status": "success"}

@app.post("/api/job/log/{job_id}")
def log_job_message(job_id: str, data: Dict[str, str]):
    job_manager.log_message(job_id, data.get("message", ""))
    return {"status": "success"}

# --- Browser/Cookie Management ---

@app.get("/api/cookies/config")
def get_cookie_config():
    config = load_cookie_config()
    return {
        "status": "success",
        "config": config,
        "state": {k: cookie_file_state(v) for k, v in config.items()},
    }

@app.post("/api/cookies/config")
def update_cookie_config(req: CookieConfigRequest):
    config = save_cookie_config(req.model_dump())
    return {
        "status": "success",
        "message": "Cookie configuration saved.",
        "config": config,
        "state": {k: cookie_file_state(v) for k, v in config.items()},
    }

@app.get("/api/vsco/session/status")
def vsco_session_status():
    profile_exists = VSCO_PROFILE_DIR.exists()
    profile_files = sum(1 for _ in VSCO_PROFILE_DIR.rglob("*")) if profile_exists else 0
    return {
        "status": "success",
        "profile_exists": profile_exists,
        "message": "VSCO session available." if profile_exists and profile_files > 0 else "No session found.",
    }

@app.post("/api/vsco/session/open-login")
def open_vsco_login_browser():
    script = BACKEND_ROOT / "scripts" / "vsco_login_browser.py"
    try:
        subprocess.Popen([sys.executable, str(script)], cwd=str(BACKEND_ROOT))
        return {"status": "success", "message": "Login browser opened."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- File/Media Management ---

@app.get("/api/images/{character}")
def list_character_images(character: str, request: Request):
    base_path = DOWNLOADS_ROOT / character
    if not base_path.exists():
        return {"images": []}

    image_files = []
    media_base = str(request.base_url).rstrip("/")
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for file in glob.glob(os.path.join(str(base_path), "**", ext), recursive=True):
            rel_path = os.path.relpath(file, str(base_path)).replace(os.sep, "/")
            image_files.append({
                "name": os.path.basename(file),
                "url": f"{media_base}/media/{quote(character)}/{quote(rel_path)}",
                "size": os.path.getsize(file),
                "folder": os.path.dirname(rel_path) or "root",
            })
    return {"images": image_files}

@app.get("/api/videos/{character}")
def list_character_videos(character: str, request: Request):
    base_path = DOWNLOADS_ROOT / character
    if not base_path.exists():
        return {"videos": []}

    videos = []
    media_base = str(request.base_url).rstrip("/")
    for pattern in ["*.mp4", "*.mov", "*.mkv", "*.webm"]:
        for file in base_path.rglob(pattern):
            rel = file.relative_to(base_path).as_posix()
            videos.append({
                "name": file.name,
                "path": str(file.resolve()),
                "folder": str(file.parent.relative_to(base_path)).replace("\\", "/") or "root",
                "size": file.stat().st_size,
                "url": f"{media_base}/media/{quote(character)}/{quote(rel)}",
            })
    return {"videos": sorted(videos, key=lambda v: v["name"].lower())}

@app.post("/api/video/extract-frames")
def extract_video_frames(req: FrameExtractionRequest):
    from scripts.extract_frames import extract_frames
    return extract_frames(
        video_path=req.video_path,
        character=req.character,
        interval_seconds=req.interval,
        max_frames=req.max_frames,
        output_subfolder=req.output_subfolder,
    )

# Static Mounting
app.mount("/media", StaticFiles(directory=str(DOWNLOADS_ROOT)), name="media")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
