# LoRA Pack UI

LoRA Pack UI is a local-first tool for collecting and preparing media for model training.

## Quick Start (Windows)

1. Clone this repository.
2. Run `install.bat` once (creates `.venv`, installs backend + frontend dependencies, installs Playwright Chromium).
3. Run `run.cmd`.
4. Open [http://localhost:5173](http://localhost:5173).

## Update Workflow

When new code is pushed, run:

- `update.bat`

This will:

1. Pull latest git changes.
2. Ensure Python virtual environment exists.
3. Install backend requirements.
4. Install frontend dependencies.
5. Install/update Playwright Chromium.

## Notes

- This project is designed to run locally.
- Runtime/user data is ignored from git (`backend/downloads`, auth/session data, local cookie config, `.venv`, caches).
- VSCO metadata JSON sidecar files are disabled by default.
