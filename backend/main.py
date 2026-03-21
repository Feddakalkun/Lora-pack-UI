from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import quote
import glob
import os
import shutil
import time
import subprocess
import sys
import threading

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

class CharacterRequest(BaseModel):
    name: str

class MoveRequest(BaseModel):
    character: str
    from_folder: str
    to_folder: str
    files: List[str]

class FrameExtractionRequest(BaseModel):
    video_path: str
    character: str
    interval: float = 1.0
    max_frames: int | None = None
    output_subfolder: str = "frames"


class CaptionRequest(BaseModel):
    character: str
    overwrite: bool = False
    model: str = "llava:7b"
    ollama_base: str = "http://127.0.0.1:11434"

# --- Endpoints ---

@app.get("/")
def index():
    return {"status": "ok", "message": "LoRA Pack Backend is purring."}

# --- Character Management ---

@app.get("/api/characters")
def list_characters():
    if not DOWNLOADS_ROOT.exists():
        return {"characters": []}
    
    # List directories in downloads folder, excluding hidden ones
    chars = [d.name for d in DOWNLOADS_ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")]
    return {"characters": sorted(chars)}

@app.post("/api/characters")
def create_character(req: CharacterRequest):
    # Sanitize name slightly
    safe_name = "".join(c for c in req.name if c.isalnum() or c in (" ", "-", "_")).strip()
    if not safe_name:
        return {"status": "error", "message": "Invalid character name."}
    
    char_path = DOWNLOADS_ROOT / safe_name
    char_path.mkdir(parents=True, exist_ok=True)
    
    # Pre-initialize pipeline folders
    for folder in ["source", "keep", "remove", "frames", "inpaint"]:
        (char_path / folder).mkdir(exist_ok=True)
        
    return {"status": "success", "message": f"Character '{safe_name}' initialized.", "name": safe_name}

# --- File/Media Curation ---

@app.post("/api/move")
def move_files(req: MoveRequest):
    char_path = DOWNLOADS_ROOT / req.character
    if not char_path.exists():
        return {"status": "error", "message": "Character not found."}

    from_dir = char_path / req.from_folder
    to_dir = char_path / req.to_folder
    to_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    errors = []

    for filename in req.files:
        src = from_dir / filename
        dst = to_dir / filename
        
        # Avoid overwriting or errors if identical
        if src == dst:
            continue
            
        try:
            if src.exists():
                # If destination exists, add a timestamp or index to avoid collision
                if dst.exists():
                    name, ext = os.path.splitext(filename)
                    dst = to_dir / f"{name}_{int(time.time())}{ext}"
                
                shutil.move(str(src), str(dst))
                moved.append(filename)
            else:
                errors.append(f"File not found: {filename}")
        except Exception as e:
            errors.append(f"Failed to move {filename}: {str(e)}")

    return {
        "status": "success",
        "moved_count": len(moved),
        "errors": errors,
        "moved": moved
    }

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


def _run_caption_subprocess(job_id: str, req: CaptionRequest):
    backend_root = Path(__file__).resolve().parent
    script_path = backend_root / "scripts" / "auto_caption.py"
    api_base = os.environ.get("API_BASE_URL")
    if not api_base:
        port = os.environ.get("BACKEND_PORT", "8000")
        api_base = f"http://127.0.0.1:{port}"
    cmd = [
        sys.executable,
        str(script_path),
        "--character",
        req.character,
        "--job-id",
        job_id,
        "--api-base",
        api_base,
        "--model",
        req.model,
        "--ollama-base",
        req.ollama_base,
    ]
    if req.overwrite:
        cmd.append("--overwrite")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(backend_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            job = job_manager.get_job(job_id)
            if job and job.get("status") not in ("success", "error"):
                msg = f"Auto-caption process crashed (code {process.returncode})."
                if stderr:
                    msg += f" {stderr[:250]}"
                job_manager.update_job(job_id, status="error", message=msg, progress=100)
        elif stdout:
            job_manager.log_message(job_id, "Auto-caption process finished.")
    except Exception as exc:
        job_manager.update_job(job_id, status="error", message=f"Caption launch error: {exc}", progress=100)


@app.post("/api/caption/start")
def caption_start(req: CaptionRequest):
    job_id = job_manager.create_job(
        url=f"caption://{req.character}",
        character=req.character,
        payload={"task": "caption", "overwrite": req.overwrite, "model": req.model},
    )
    job_manager.update_job(job_id, status="running", progress=1, message="Queued caption job...")
    thread = threading.Thread(target=_run_caption_subprocess, args=(job_id, req), daemon=True)
    thread.start()
    return {"status": "success", "job_id": job_id, "message": "Auto-caption started."}

# Static Mounting
app.mount("/media", StaticFiles(directory=str(DOWNLOADS_ROOT)), name="media")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("BACKEND_PORT", "8000"))
    except ValueError:
        port = 8000
    uvicorn.run("main:app", host=host, port=port, reload=True)
