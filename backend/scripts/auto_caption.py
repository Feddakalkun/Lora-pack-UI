import argparse
import base64
from pathlib import Path
from typing import Dict, List

try:
    import requests
except ImportError:
    requests = None


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
SKIP_DIRS = {"remove", ".auth", ".config", "__pycache__"}


def _log_remote(msg: str, job_id: str, api_base: str):
    print(f"[CAPTION] {msg}")
    if job_id and api_base and requests:
        try:
            requests.post(f"{api_base}/api/job/log/{job_id}", json={"message": msg}, timeout=8)
        except Exception:
            pass


def _update_remote(status: str, msg: str, progress: int, job_id: str, api_base: str, result: Dict | None = None):
    if job_id and api_base and requests:
        try:
            payload = {"status": status, "message": msg, "progress": progress}
            if result is not None:
                payload["result"] = result
            requests.post(f"{api_base}/api/job/update/{job_id}", json=payload, timeout=8)
        except Exception:
            pass


def _collect_images(character_root: Path) -> List[Path]:
    items: List[Path] = []
    if not character_root.exists():
        return items
    for p in character_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        if any(part.lower() in SKIP_DIRS for part in p.parts):
            continue
        items.append(p)
    return sorted(items)


def _caption_with_ollama(image_path: Path, model: str, ollama_base: str, prompt: str) -> str:
    if requests is None:
        raise RuntimeError("requests is not installed in backend environment")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [base64.b64encode(image_path.read_bytes()).decode("ascii")],
    }
    resp = requests.post(f"{ollama_base.rstrip('/')}/api/generate", json=payload, timeout=180)
    if resp.status_code >= 400:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama returned empty caption text")
    return text


def auto_caption_character(
    character: str,
    job_id: str = "",
    api_base: str = "",
    overwrite: bool = False,
    model: str = "llava:7b",
    ollama_base: str = "http://127.0.0.1:11434",
) -> Dict:
    backend_root = Path(__file__).resolve().parent.parent
    character_root = backend_root / "downloads" / character

    if not character_root.exists():
        msg = f"Character folder not found: {character_root}"
        _update_remote("error", msg, 100, job_id, api_base)
        return {"status": "error", "message": msg}

    prompt = (
        "Write a concise training caption for this person image. "
        "Use comma-separated tags focused on: subject appearance, clothing, pose, camera framing, "
        "background, lighting, and style. No hashtags, no full sentences."
    )

    images = _collect_images(character_root)
    if not images:
        msg = f"No images found under {character_root}"
        _update_remote("error", msg, 100, job_id, api_base)
        return {"status": "error", "message": msg}

    _log_remote(f"Found {len(images)} images for captioning.", job_id, api_base)
    _log_remote(f"Using Ollama model: {model}", job_id, api_base)
    _update_remote("running", "Starting auto-caption...", 2, job_id, api_base)

    created = 0
    skipped = 0
    failed = 0

    for idx, img in enumerate(images, start=1):
        txt_path = img.with_suffix(".txt")
        if txt_path.exists() and not overwrite:
            skipped += 1
            progress = int((idx / max(1, len(images))) * 95)
            _update_remote("running", f"Captioning... ({idx}/{len(images)})", progress, job_id, api_base)
            continue

        try:
            caption = _caption_with_ollama(img, model=model, ollama_base=ollama_base, prompt=prompt)
            txt_path.write_text(caption + "\n", encoding="utf-8")
            created += 1
        except Exception as exc:
            failed += 1
            _log_remote(f"Failed {img.name}: {exc}", job_id, api_base)

        progress = int((idx / max(1, len(images))) * 95)
        _update_remote("running", f"Captioning... ({idx}/{len(images)})", progress, job_id, api_base)

    msg = f"Auto-caption done. Created: {created}, skipped: {skipped}, failed: {failed}."
    status = "success" if created > 0 or skipped > 0 else "error"
    _update_remote(
        status,
        msg,
        100,
        job_id,
        api_base,
        result={"created": created, "skipped": skipped, "failed": failed, "character": character},
    )
    return {"status": status, "message": msg, "created": created, "skipped": skipped, "failed": failed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--character", required=True)
    parser.add_argument("--job-id", default="")
    parser.add_argument("--api-base", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--model", default="llava:7b")
    parser.add_argument("--ollama-base", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    result = auto_caption_character(
        character=args.character,
        job_id=args.job_id,
        api_base=args.api_base,
        overwrite=args.overwrite,
        model=args.model,
        ollama_base=args.ollama_base,
    )
    if str(result.get("status", "")).lower() != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
