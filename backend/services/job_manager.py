import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_job(self, url: str, character: str, payload: Dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex
        with self.lock:
            self.jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "progress": 0,
                "message": "Queued",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "logs": [],
                "request": {
                    "url": url,
                    "character": character,
                    **payload
                },
                "result": None
            }
        self.log_message(job_id, f"Job initialized for {url}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job_id: str, status: str = None, progress: int = None, message: str = None, result: Any = None):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            
            if status: job["status"] = status
            if progress is not None: job["progress"] = progress
            if message: job["message"] = message
            if result is not None: job["result"] = result
            
            job["updated_at"] = datetime.utcnow().isoformat() + "Z"

    def log_message(self, job_id: str, message: str):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            stamp = datetime.now().strftime("%H:%M:%S")
            job.setdefault("logs", []).append(f"[{stamp}] {message}")
            job["updated_at"] = datetime.utcnow().isoformat() + "Z"

# Global instance
job_manager = JobManager()
