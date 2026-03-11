import subprocess
import sys
import os
import threading
from pathlib import Path

def main():
    # This script is located in backend/services/
    # We need the project root (2 levels up)
    root = Path(__file__).resolve().parent.parent.parent
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print(f"Error: Virtual environment not found at {venv_python}")
        return

    print("==============================================")
    print("=      LORA PACK STUDIO: UNIFIED SESSION     =")
    print("==============================================")
    print("\n🚀 Initializing Services...")

    # Start Backend
    backend_proc = subprocess.Popen(
        [str(venv_python), "main.py"],
        cwd=str(root / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Start Frontend
    # we need to make sure npm is available
    frontend_proc = subprocess.Popen(
        ["cmd", "/c", "npm run dev"],
        cwd=str(root / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def print_logs(proc, label):
        try:
            for line in iter(proc.stdout.readline, ""):
                if line:
                    print(f"[{label}] {line.strip()}")
        except:
            pass

    t1 = threading.Thread(target=print_logs, args=(backend_proc, "BACKEND"), daemon=True)
    t2 = threading.Thread(target=print_logs, args=(frontend_proc, "FRONTEND"), daemon=True)
    t1.start()
    t2.start()

    print("\n✅ Studio is Live. Press Ctrl+C to stop everything.\n")
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down Studio...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
