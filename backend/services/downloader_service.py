import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from services.job_manager import job_manager

class DownloaderService:
    def dispatch_and_run(self, job_id: str, url: str, character: str, vsco_cookies: Optional[str] = None, tiktok_cookies: Optional[str] = None):
        """
        Dispatches the download to a standalone background process.
        Using a separate process avoids asyncio/event-loop conflicts (like NotImplementedError on Windows).
        """
        # Determine script to run
        script_name = ""
        cookies = ""
        
        if "vsco.co" in url.lower():
            script_name = "download_vsco.py"
            cookies = vsco_cookies or ""
        elif "tiktok.com" in url.lower():
            script_name = "download_tiktok.py"
            cookies = tiktok_cookies or ""
        else:
            job_manager.update_job(job_id, status="error", message="Unsupported URL platform.")
            return

        # Run in a thread to keep the API responsive while managing the process
        thread = threading.Thread(
            target=self._launch_subprocess,
            args=(job_id, script_name, url, character, cookies),
            daemon=True
        )
        thread.start()

    def _launch_subprocess(self, job_id: str, script_name: str, url: str, character: str, cookies: str):
        job_manager.log_message(job_id, f"Launching process-isolated engine: {script_name}")
        job_manager.update_job(job_id, status="running", progress=5, message="Initializing engine...")
        
        backend_root = Path(__file__).resolve().parent.parent
        script_path = backend_root / "scripts" / script_name
        
        # Build command
        # Use sys.executable to ensure we use the same venv
        cmd = [
            sys.executable,
            str(script_path),
            url,
            "--character", character,
            "--job-id", job_id,
            "--api-base", "http://localhost:8000"
        ]
        
        if cookies:
            cmd.extend(["--cookies", cookies])
            
        try:
            # We use Popen so it runs truly in the background
            # We don't wait for it here, the script will report back via API
            process = subprocess.Popen(
                cmd,
                cwd=str(backend_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Optionally log stdout/stderr for server-side debugging
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                 print(f"DEBUG: Process {script_name} failed with code {process.returncode}")
                 if stderr: print(f"DEBUG: Stderr: {stderr}")
                 
                 job = job_manager.get_job(job_id)
                 if job and job.get("status") != "success":
                     err_msg = f"Engine process crashed (code {process.returncode})."
                     if "yt-dlp" in stderr: err_msg = "TikTok/YT-DLP blocked or error."
                     job_manager.update_job(job_id, status="error", message=err_msg)
            else:
                 print(f"DEBUG: Process {script_name} finished successfully.")            
        except Exception as e:
            error_str = f"Process Launch Error: {str(e)}"
            job_manager.update_job(job_id, status="error", message=error_str)
            job_manager.log_message(job_id, error_str)

# Global instance
downloader_service = DownloaderService()
