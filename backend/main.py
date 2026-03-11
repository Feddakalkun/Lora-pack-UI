from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from urllib.parse import quote
from datetime import datetime
import glob
import os
import subprocess
import sys
import threading
import uuid

from scripts.cookie_store import (
    cookie_file_state,
    load_cookie_config,
    resolve_cookie_file,
    save_cookie_config,
)

app = FastAPI(title="LoRA Pack UI Backend")
BACKEND_ROOT = Path(__file__).resolve().parent
DOWNLOADS_ROOT = BACKEND_ROOT / "downloads"
VSCO_PROFILE_DIR = BACKEND_ROOT / ".auth" / "vsco_playwright_profile"

DOWNLOAD_JOBS: dict[str, dict] = {}
DOWNLOAD_LOCK = threading.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/")
def index():
    return {"status": "ok", "message": "Backend is running! Ready for API requests."}


def _job_log(job_id: str, message: str):
    with DOWNLOAD_LOCK:
        job = DOWNLOAD_JOBS.get(job_id)
        if not job:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        job.setdefault("logs", []).append(f"[{stamp}] {message}")
        job["updated_at"] = datetime.utcnow().isoformat() + "Z"


def _dispatch_download(url: str, character: str, vsco_cookies_file: str | None, tiktok_cookies_file: str | None) -> dict:
    if "vsco.co" in url:
        from scripts.download_vsco import download_vsco

        resolved = resolve_cookie_file("vsco", vsco_cookies_file)
        return download_vsco(url, character, resolved)

    if "tiktok.com" in url:
        from scripts.download_tiktok import download_tiktok

        resolved = resolve_cookie_file("tiktok", tiktok_cookies_file)
        return download_tiktok(url, character, resolved)

    return {"status": "error", "message": f"No scraper implemented for {url} yet."}


def _run_download_job(job_id: str, payload: dict):
    with DOWNLOAD_LOCK:
        job = DOWNLOAD_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["progress"] = 35
        job["updated_at"] = datetime.utcnow().isoformat() + "Z"

    _job_log(job_id, f"Started download for {payload.get('url', '')}")

    try:
        result = _dispatch_download(
            url=str(payload.get("url", "")),
            character=str(payload.get("character", "Unsorted")),
            vsco_cookies_file=payload.get("vsco_cookies_file"),
            tiktok_cookies_file=payload.get("tiktok_cookies_file"),
        )

        final_status = "success" if str(result.get("status", "")).lower() == "success" else "error"
        msg = str(result.get("message", "Finished"))

        with DOWNLOAD_LOCK:
            job = DOWNLOAD_JOBS.get(job_id)
            if job:
                job["status"] = final_status
                job["progress"] = 100
                job["message"] = msg
                job["result"] = result
                job["updated_at"] = datetime.utcnow().isoformat() + "Z"

        _job_log(job_id, msg)
    except Exception as exc:
        err = f"error: {exc}"
        with DOWNLOAD_LOCK:
            job = DOWNLOAD_JOBS.get(job_id)
            if job:
                job["status"] = "error"
                job["progress"] = 100
                job["message"] = err
                job["result"] = {"status": "error", "message": err}
                job["updated_at"] = datetime.utcnow().isoformat() + "Z"

        _job_log(job_id, err)


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
    config = save_cookie_config(
        {
            "vsco": req.vsco,
            "tiktok": req.tiktok,
            "instagram": req.instagram,
        }
    )
    return {
        "status": "success",
        "message": "Cookie configuration saved.",
        "config": config,
        "state": {k: cookie_file_state(v) for k, v in config.items()},
    }


@app.get("/api/vsco/session/status")
def vsco_session_status():
    profile_exists = VSCO_PROFILE_DIR.exists()
    profile_files = 0
    if profile_exists:
        try:
            profile_files = sum(1 for _ in VSCO_PROFILE_DIR.rglob("*"))
        except Exception:
            profile_files = 0
    return {
        "status": "success",
        "profile_dir": str(VSCO_PROFILE_DIR),
        "profile_exists": profile_exists,
        "profile_files": profile_files,
        "message": "VSCO session profile looks available." if profile_exists and profile_files > 0 else "No saved VSCO session yet.",
    }


@app.post("/api/vsco/session/open-login")
def open_vsco_login_browser():
    script = BACKEND_ROOT / "scripts" / "vsco_login_browser.py"
    if not script.exists():
        return {"status": "error", "message": f"VSCO login helper not found: {script}"}

    try:
        subprocess.Popen([sys.executable, str(script)], cwd=str(BACKEND_ROOT))
        return {
            "status": "success",
            "message": "Opened VSCO login browser. Sign in there once, then close that window.",
        }
    except Exception as exc:
        return {"status": "error", "message": f"error: Could not open VSCO login browser: {exc}"}


@app.post("/api/download")
def download_sync(req: DownloadRequest):
    return _dispatch_download(req.url, req.character, req.vsco_cookies_file, req.tiktok_cookies_file)


@app.post("/api/download/start")
def download_start(req: DownloadRequest):
    job_id = uuid.uuid4().hex
    with DOWNLOAD_LOCK:
        DOWNLOAD_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 5,
            "message": "Queued",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "logs": [],
            "request": {
                "url": req.url,
                "character": req.character,
            },
        }

    thread = threading.Thread(
        target=_run_download_job,
        args=(job_id, req.model_dump()),
        daemon=True,
    )
    thread.start()

    _job_log(job_id, "Job queued")

    return {
        "status": "success",
        "job_id": job_id,
        "message": "Download started.",
    }


@app.get("/api/download/status/{job_id}")
def download_status(job_id: str):
    with DOWNLOAD_LOCK:
        job = DOWNLOAD_JOBS.get(job_id)
        if not job:
            return {"status": "error", "message": "Job not found."}
        return {"status": "success", "job": job}


@app.post("/api/video/extract-frames")
def extract_video_frames(req: FrameExtractionRequest):
    from scripts.extract_frames import extract_frames

    result = extract_frames(
        video_path=req.video_path,
        character=req.character,
        interval_seconds=req.interval,
        max_frames=req.max_frames,
        output_subfolder=req.output_subfolder,
    )
    return result


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
            image_files.append(
                {
                    "name": os.path.basename(file),
                    "url": f"{media_base}/media/{quote(character)}/{quote(rel_path)}",
                    "size": os.path.getsize(file),
                    "folder": os.path.dirname(rel_path) or "root",
                }
            )

    return {"images": image_files}


@app.get("/api/videos/{character}")
def list_character_videos(character: str, request: Request):
    base_path = DOWNLOADS_ROOT / character
    if not base_path.exists():
        return {"videos": []}

    videos = []
    media_base = str(request.base_url).rstrip("/")
    patterns = ["*.mp4", "*.mov", "*.mkv", "*.webm"]
    for pattern in patterns:
        for file in base_path.rglob(pattern):
            if not file.is_file():
                continue
            rel = file.relative_to(base_path).as_posix()
            videos.append(
                {
                    "name": file.name,
                    "path": str(file.resolve()),
                    "folder": str(file.parent.relative_to(base_path)).replace("\\", "/") or "root",
                    "size": file.stat().st_size,
                    "url": f"{media_base}/media/{quote(character)}/{quote(rel)}",
                }
            )

    videos.sort(key=lambda v: v["name"].lower())
    return {"videos": videos}


DOWNLOADS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(DOWNLOADS_ROOT)), name="media")


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("BACKEND_PORT", "8000"))
    except ValueError:
        port = 8000
    uvicorn.run("main:app", host=host, port=port, reload=True)
