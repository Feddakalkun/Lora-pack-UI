import argparse
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


def _log_remote(msg: str, job_id: str, api_base: str):
    print(f"[TIKTOK] {msg}")
    if job_id and api_base and requests:
        try:
            requests.post(f"{api_base}/api/job/log/{job_id}", json={"message": msg}, timeout=8)
        except Exception:
            pass


def _update_remote(status: str, msg: str, progress: int, job_id: str, api_base: str, result: Dict = None):
    if job_id and api_base and requests:
        try:
            payload = {"status": status, "message": msg, "progress": progress}
            if result:
                payload["result"] = result
            requests.post(f"{api_base}/api/job/update/{job_id}", json=payload, timeout=8)
        except Exception:
            pass


def _sanitize(value: str, default: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._ -]+", "_", (value or "").strip())
    return cleaned or default


def _extract_tiktok_meta(url: str) -> Tuple[str, str, bool]:
    text = (url or "").strip()
    if not text:
        raise ValueError("TikTok URL is required.")

    creator = "unknown"
    video_id = "unknown"
    is_profile = "/video/" not in text.lower()

    m_creator = re.search(r"tiktok\.com/@([^/?#]+)", text, flags=re.IGNORECASE)
    if m_creator:
        creator = _sanitize(m_creator.group(1), "unknown").lower()

    m_video = re.search(r"/video/(\d+)", text)
    if m_video:
        video_id = m_video.group(1)
        is_profile = False

    return creator, video_id, is_profile


def _count_video_files(folder: Path) -> int:
    count = 0
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            count += 1
    return count


def _find_latest_video(folder: Path) -> Optional[Path]:
    candidates = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _build_base_cmd(output_template: str, archive_file: Path, is_profile: bool) -> list[str]:
    cmd = [
        "yt-dlp",
        "--no-progress",
        "--ignore-errors",
        "--no-overwrites",
        "--restrict-filenames",
        "--download-archive",
        str(archive_file),
        "--merge-output-format",
        "mp4",
        "--format",
        "bv*+ba/b[ext=mp4]/b",
        "-o",
        output_template,
    ]
    cmd.append("--yes-playlist" if is_profile else "--no-playlist")
    return cmd


def download_tiktok(
    url: str,
    character: str = "Unsorted",
    cookies_file: str | None = None,
    job_id: str | None = None,
    api_base: str | None = None,
) -> Dict:
    try:
        creator, video_id, is_profile = _extract_tiktok_meta(url)
        safe_char = _sanitize(character, "Unsorted")

        backend_root = Path(__file__).resolve().parent.parent
        downloads_root = backend_root / "downloads" / safe_char / "tiktok" / creator
        downloads_root.mkdir(parents=True, exist_ok=True)
        archive_file = downloads_root / "tiktok-archive.txt"

        if is_profile:
            output_template = str(downloads_root / "%(id)s.%(ext)s")
            _log_remote(f"Pipeline: TikTok Profile Sync [@{creator}]", job_id or "", api_base or "")
        else:
            output_template = str(downloads_root / f"{video_id}.%(ext)s")
            _log_remote(f"Pipeline: TikTok Post Sync [@{creator}]", job_id or "", api_base or "")

        base_cmd = _build_base_cmd(output_template, archive_file, is_profile=is_profile)
        before_videos = _count_video_files(downloads_root)

        strategies = []
        manual = (cookies_file or "").strip()
        if manual and Path(manual).exists():
            strategies.append(("cookies:file", ["--cookies", manual]))
        strategies.extend(
            [
                ("native:no-cookies", []),
                ("native:chrome", ["--cookies-from-browser", "chrome"]),
                ("native:edge", ["--cookies-from-browser", "edge"]),
            ]
        )

        last_err = "No strategy succeeded."
        for idx, (label, args) in enumerate(strategies, start=1):
            _log_remote(f"Attempt {idx}/{len(strategies)} via {label}...", job_id or "", api_base or "")
            _update_remote("running", f"Trying {label}...", min(90, 10 + idx * 20), job_id or "", api_base or "")

            full_cmd = base_cmd + args + [url.strip()]
            proc = subprocess.run(full_cmd, capture_output=True, text=True)

            after_videos = _count_video_files(downloads_root)
            if proc.returncode == 0 and after_videos >= before_videos:
                newest = _find_latest_video(downloads_root)
                if newest is not None:
                    new_count = max(0, after_videos - before_videos)
                    if is_profile:
                        msg = f"TikTok profile sync success: +{new_count} videos (total {after_videos}) saved to {safe_char}."
                    else:
                        msg = f"TikTok Sync Success: {newest.name} saved to {safe_char}."
                    _update_remote(
                        "success",
                        msg,
                        100,
                        job_id or "",
                        api_base or "",
                        {"video_path": str(newest), "new_videos": new_count, "total_videos": after_videos},
                    )
                    return {"status": "success", "message": msg}

            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            last_err = (stderr or stdout or f"yt-dlp failed with code {proc.returncode}")[:400]
            _log_remote(f"{label} failed: {last_err}", job_id or "", api_base or "")

        err = f"TikTok download failed: {last_err}"
        _update_remote("error", err, 100, job_id or "", api_base or "")
        return {"status": "error", "message": err}

    except Exception as exc:
        msg = str(exc)
        _update_remote("error", msg, 100, job_id or "", api_base or "")
        return {"status": "error", "message": msg}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--character", default="Unsorted")
    parser.add_argument("--cookies", default="")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--api-base", default="")
    args = parser.parse_args()
    download_tiktok(args.url, args.character, args.cookies, args.job_id, args.api_base)


if __name__ == "__main__":
    main()
