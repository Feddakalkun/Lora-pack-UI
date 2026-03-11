import argparse
import os
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional

# --- API Reporting Helpers ---
try:
    import requests
except ImportError:
    requests = None

def _log_remote(msg: str, job_id: str, api_base: str):
    print(f"[DEBUG] {msg}")
    if job_id and api_base and requests:
        try:
            requests.post(f"{api_base}/api/job/log/{job_id}", json={"message": msg}, timeout=5)
        except: pass

def _update_remote(status: str, msg: str, progress: int, job_id: str, api_base: str, result: Dict = None):
    if job_id and api_base and requests:
        try:
            payload = {"status": status, "message": msg, "progress": progress}
            if result: payload["result"] = result
            requests.post(f"{api_base}/api/job/update/{job_id}", json=payload, timeout=5)
        except: pass

# --- Core Logic ---

def _sanitize(value: str, default: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._ -]+", "_", (value or "").strip())
    return cleaned or default

def _extract_tiktok_meta(url: str) -> tuple[str, str]:
    text = (url or "").strip()
    if not text: raise ValueError("TikTok URL is required.")
    
    creator = "unknown"
    video_id = "unknown"

    m_creator = re.search(r"tiktok\.com/@([^/?#]+)", text, flags=re.IGNORECASE)
    if m_creator: creator = _sanitize(m_creator.group(1), "unknown").lower()

    m_video = re.search(r"/video/(\d+)", text)
    if m_video: video_id = m_video.group(1)

    return creator, video_id

def download_tiktok(url: str, character: str = "Unsorted", cookies_file: str | None = None, job_id: str | None = None, api_base: str | None = None) -> Dict:
    try:
        creator, video_id = _extract_tiktok_meta(url)
        safe_char = _sanitize(character, "Unsorted")
        
        backend_root = Path(__file__).resolve().parent.parent
        downloads_root = backend_root / "downloads" / safe_char / "tiktok" / creator
        downloads_root.mkdir(parents=True, exist_ok=True)

        _log_remote(f"Pipeline: TikTok Sync [@{creator}]", job_id, api_base)

        output_template = str(downloads_root / f"{video_id}.%(ext)s")
        
        # Base Command
        base_cmd = [
            "yt-dlp",
            "--no-progress",
            "--merge-output-format", "mp4",
            "-o", output_template
        ]

        # Strategies: 
        # 1. No cookies (Generic)
        # 2. Chrome
        # 3. Edge
        strategies = [
            ("native:no-cookies", []),
            ("native:chrome", ["--cookies-from-browser", "chrome"]),
            ("native:edge", ["--cookies-from-browser", "edge"]),
        ]

        success = False
        last_err = ""

        for label, args in strategies:
            _log_remote(f"Attempting TikTok download via {label}...", job_id, api_base)
            full_cmd = base_cmd + args + [url.strip()]
            
            proc = subprocess.run(full_cmd, capture_output=True, text=True)
            if proc.returncode == 0:
                files = list(downloads_root.glob(f"{video_id}.*"))
                if files:
                    video_path = files[0]
                    msg = f"TikTok Sync Success: {video_path.name} saved to {safe_char}."
                    _update_remote("success", msg, 100, job_id, api_base, {"video_path": str(video_path)})
                    return {"status": "success", "message": msg}
            
            last_err = (proc.stderr or proc.stdout or "Unknown failure").strip()
            if "DPAPI" in last_err:
                _log_remote(f"Browser access denied ({label}): {last_err[:100]}", job_id, api_base)
            else:
                _log_remote(f"Strategy {label} failed: {last_err[:100]}", job_id, api_base)

        _update_remote("error", f"Synd failed: {last_err[:200]}", 100, job_id, api_base)
        return {"status": "error", "message": f"All strategies failed: {last_err}"}

    except Exception as e:
        _update_remote("error", str(e), 100, job_id, api_base)
        return {"status": "error", "message": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--character", default="Unsorted")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--api-base", default="")
    args = parser.parse_args()
    download_tiktok(args.url, args.character, None, args.job_id, args.api_base)

if __name__ == "__main__":
    main()