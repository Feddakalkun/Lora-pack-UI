import subprocess
import sys
import os
import signal
from pathlib import Path

def main():
    root = Path(__file__).parent
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print(f"Error: Virtual environment not found at {venv_python}")
        return

    print("🚀 Starting LoRA Pack Studio...")

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
    frontend_proc = subprocess.Popen(
        ["cmd", "/c", "npm run dev"],
        cwd=str(root / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    def print_logs(proc, label):
        for line in iter(proc.stdout.readline, ""):
            if line:
                print(f"[{label}] {line.strip()}")

    # We'll use threads to print logs from both simultaneously
    import threading
    t1 = threading.Thread(target=print_logs, args=(backend_proc, "BACKEND"), daemon=True)
    t2 = threading.Thread(target=print_logs, args=(frontend_proc, "FRONTEND"), daemon=True)
    t1.start()
    t2.start()

    print("\n--- Both services are running ---\n")
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    main()
