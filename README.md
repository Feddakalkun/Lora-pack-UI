# LoRA Pack UI

LoRA Pack UI is a local-first tool for collecting and preparing media for model training.

## Quick Start (Windows)

1. Clone this repository.
2. Run `install.bat` once (creates `.venv`, installs backend + frontend dependencies, installs Playwright Chromium).
3. Run `run.cmd`.
4. Optional for side-by-side clones: `run.cmd 8001 5174` (backend port first, frontend port second).
5. Open the frontend URL shown in terminal (default [http://localhost:5173](http://localhost:5173)).

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
- `run.cmd` accepts optional ports: `run.cmd <backend_port> <frontend_port>`.

## Auto Caption (Screenshots / Frames)

You can auto-caption images from the Gallery tab (new text icon button).

Requirements:

1. Install Ollama: https://ollama.com/
2. Pull a vision model once:
   - `ollama pull llava:7b`
3. Keep Ollama running locally (default: `http://127.0.0.1:11434`)

Then in the app:

1. Select your character.
2. Go to **Curation & Gallery**.
3. Click the **Auto Caption** button.

The backend writes one `.txt` caption next to each image file.
