import os
import sys
import re
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Tuple, List, Optional

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

# --- Core Logic from "working" legacy scripts ---

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

def extract_username(url: str) -> str:
    match = re.search(r"vsco\.co/([^/?#\s]+)", url)
    if not match: raise ValueError(f"Could not extract VSCO username from URL: {url}")
    return match.group(1).lower()

def _sanitize(txt: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._ -]+", "_", txt or "Unsorted")

def _count_images(d: Path) -> int:
    return len([f for f in d.glob("*") if f.is_file()])

def _export_cookies(job_id: str, api_base: str) -> Optional[Path]:
    try:
        import browser_cookie3
        _log_remote("Exporting VSCO session from Chrome/Edge...", job_id, api_base)
        
        # We'll try to get all cookies for vsco.co
        jar = browser_cookie3.chrome(domain_name="vsco.co")
        if not jar:
            jar = browser_cookie3.edge(domain_name="vsco.co")
            
        if jar:
            # Create a temporary Netscape format cookie file
            cookie_path = Path(__file__).parent.parent / "downloads" / "vsco_cookies.txt"
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for c in jar:
                    # Domain, IncludeSubdomains, Path, Secure, Expiry, Name, Value
                    secure = "TRUE" if c.secure else "FALSE"
                    expiry = str(int(c.expires)) if c.expires else "0"
                    f.write(f"{c.domain}\tTRUE\t{c.path}\t{secure}\t{expiry}\t{c.name}\t{c.value}\n")
            
            _log_remote(f"Session cookies exported to {cookie_path.name}", job_id, api_base)
            return cookie_path
    except Exception as e:
        _log_remote(f"Cookie export skipped: {e}", job_id, api_base)
    return None

def download_vsco(url: str, character: str = "Unsorted", cookies_file: str | None = None, job_id: str | None = None, api_base: str | None = None) -> Dict:
    try:
        username = extract_username(url)
        gallery_url = f"https://vsco.co/{username}/gallery"
        safe_char = _sanitize(character)
        
        backend_root = Path(__file__).resolve().parent.parent
        base_dir = backend_root / "downloads" / safe_char / "source"
        base_dir.mkdir(parents=True, exist_ok=True)
        archive = base_dir.parent / f"vsco_{username}_archive.txt"

        _log_remote(f"Pipeline: VSCO Ingestion Module (@{username})", job_id, api_base)

        # Build gallery-dl command
        # This is based on the logic from vsco_selector.py which you said was working
        cmd = [
            "gallery-dl",
            "--directory", str(base_dir),
            "--download-archive", str(archive),
            "--write-metadata"
        ]

        # Try with different cookie sources
        cookie_attempts = []
        
        # 1. Manual/Auto-exported cookies
        auto_cookies = _export_cookies(job_id, api_base)
        if auto_cookies:
            cookie_attempts.append(("exported", ["--cookies", str(auto_cookies)]))
        
        # 2. Direct browser access (native to gallery-dl)
        cookie_attempts.append(("native:chrome", ["--cookies-from-browser", "chrome"]))
        cookie_attempts.append(("native:edge", ["--cookies-from-browser", "edge"]))
        cookie_attempts.append(("no-cookies", []))

        success = False
        for label, cookie_args in cookie_attempts:
            _log_remote(f"Initiating gallery-dl probe via {label}...", job_id, api_base)
            full_cmd = cmd + cookie_args + [gallery_url]
            
            try:
                proc = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        line = line.strip()
                        if line:
                             _log_remote(line, job_id, api_base)
                             # Optional: Try to guess progress based on output
                             if "Downloaded" in line or line.startswith("#"):
                                 _update_remote("running", "Downloading assets...", 50, job_id, api_base)
                
                proc.wait()
                
                count = _count_images(base_dir)
                if proc.returncode == 0 or count > 0:
                    _log_remote(f"Probe successful! {count} total assets indexed in folder.", job_id, api_base)
                    success = True
                    break
            except Exception as e:
                _log_remote(f"Probe {label} failed: {e}", job_id, api_base)

        if success:
            msg = f"Ingestion Complete: {count} assets synced to {safe_char}."
            _update_remote("success", msg, 100, job_id, api_base)
            return {"status": "success", "message": msg}

        # Fallback to local browser if you have it open
        _log_remote("All automated probes failed. VSCO is aggressively blocking the server.", job_id, api_base)
        _log_remote("TIP: Make sure you are signed in to VSCO in Chrome on this machine.", job_id, api_base)
        
        err = "Ingestion Blocked: VSCO denied all sync attempts. Open VSCO in Chrome to refresh session."
        _update_remote("error", err, 100, job_id, api_base)
        return {"status": "error", "message": err}

    except Exception as e:
        _update_remote("error", str(e), 100, job_id, api_base)
        return {"status": "error", "message": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--character", default="Unsorted")
    parser.add_argument("--cookies", default="")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--api-base", default="")
    args = parser.parse_args()
    download_vsco(args.url, args.character, args.cookies, args.job_id, args.api_base)

if __name__ == "__main__":
    main()
