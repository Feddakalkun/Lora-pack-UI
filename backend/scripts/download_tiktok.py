import argparse
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional


def _sanitize_name(value: str, default: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._ -]+", "_", (value or "").strip())
    return cleaned or default


def _extract_tiktok_meta(url: str) -> tuple[str, str]:
    text = (url or "").strip()
    if not text:
        raise ValueError("TikTok URL is required.")
    if "tiktok.com" not in text.lower():
        raise ValueError("URL must be from tiktok.com.")

    creator = "unknown_creator"
    video_id = "unknown_video"

    creator_match = re.search(r"tiktok\.com/@([^/?#]+)", text, flags=re.IGNORECASE)
    if creator_match:
        creator = _sanitize_name(creator_match.group(1), "unknown_creator").lower()

    video_match = re.search(r"/video/(\d+)", text)
    if video_match:
        video_id = video_match.group(1)

    return creator, video_id


def _extract_path_from_yt_dlp_output(raw_output: str) -> Optional[Path]:
    for line in (raw_output or "").splitlines():
        text = line.strip()
        if text and (":\\" in text or text.startswith("/")):
            p = Path(text)
            if p.exists():
                return p
    return None


def download_tiktok(url: str, character: str = "Unsorted", cookies_file: str | None = None) -> Dict:
    """
    Download a TikTok video using yt-dlp into:
    backend/downloads/<character>/tiktok/<creator>/
    """
    try:
        creator, video_id = _extract_tiktok_meta(url)
        safe_character = _sanitize_name(character, "Unsorted")
        downloads_root = Path(__file__).resolve().parent.parent / "downloads" / safe_character / "tiktok" / creator
        downloads_root.mkdir(parents=True, exist_ok=True)

        output_template = str(downloads_root / f"{video_id}.%(ext)s")
        command = [
            "yt-dlp",
            "--no-progress",
            "--no-warnings",
            "--merge-output-format",
            "mp4",
            "--print",
            "after_move:filepath",
            "-o",
            output_template,
        ]

        cookie_path = (cookies_file or "").strip()
        if cookie_path:
            candidate = Path(cookie_path)
            if candidate.exists() and candidate.is_file():
                command += ["--cookies", str(candidate)]

        command.append(url.strip())

        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "yt-dlp failed").strip()
            return {
                "status": "error",
                "message": f"error: yt-dlp failed: {stderr[:1400]}",
            }

        downloaded = _extract_path_from_yt_dlp_output(proc.stdout)
        if downloaded is None:
            candidates = sorted(downloads_root.glob(f"{video_id}.*"))
            downloaded = candidates[0] if candidates else None

        if downloaded is None:
            return {
                "status": "error",
                "message": "error: TikTok download completed but output file was not found.",
            }

        return {
            "status": "success",
            "message": f"Downloaded TikTok video to {downloaded}",
            "video_path": str(downloaded),
            "character": safe_character,
            "creator": creator,
            "video_id": video_id,
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "error: yt-dlp is not installed or not on PATH.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"error: {exc}",
        }


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Download one TikTok video with yt-dlp.")
    parser.add_argument("url", help="TikTok URL, e.g. https://www.tiktok.com/@user/video/123...")
    parser.add_argument("--character", default="Unsorted", help="Character folder name.")
    parser.add_argument("--cookies-file", default="", help="Optional Netscape cookie file path.")
    args = parser.parse_args()

    result = download_tiktok(args.url, args.character, args.cookies_file)
    print(result.get("message", ""))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(_cli())