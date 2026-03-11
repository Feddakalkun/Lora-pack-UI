import argparse
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional


def _sanitize_name(value: str, default: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._ -]+", "_", (value or "").strip())
    return cleaned or default


def _count_generated(output_dir: Path, stem: str) -> int:
    return len(list(output_dir.glob(f"{stem}_frame_*.jpg")))


def _extract_with_ffmpeg(video_path: Path, output_dir: Path, interval_seconds: float, max_frames: Optional[int]) -> Dict:
    if interval_seconds <= 0:
        interval_seconds = 1.0

    fps_value = 1.0 / interval_seconds
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", video_path.stem)
    pattern = str(output_dir / f"{stem}_frame_%06d.jpg")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps_value}",
        "-q:v",
        "2",
    ]
    if max_frames is not None and max_frames > 0:
        command += ["-frames:v", str(max_frames)]
    command.append(pattern)

    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        return {"status": "error", "message": f"error: ffmpeg failed: {err[:1400]}"}

    count = _count_generated(output_dir, stem)
    if count == 0:
        return {"status": "error", "message": "error: ffmpeg completed but no frames were generated."}

    return {
        "status": "success",
        "message": f"Extracted {count} frame(s) with ffmpeg to {output_dir}",
        "frames": count,
        "output_dir": str(output_dir),
    }


def _extract_with_cv2(video_path: Path, output_dir: Path, interval_seconds: float, max_frames: Optional[int]) -> Dict:
    try:
        import cv2
    except Exception:
        return {
            "status": "error",
            "message": "error: OpenCV is not installed, and ffmpeg was unavailable or failed.",
        }

    if interval_seconds <= 0:
        interval_seconds = 1.0

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"status": "error", "message": "error: Could not open video file."}

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    every_n = max(1, int(round(interval_seconds * fps)))
    frame_index = 0
    saved = 0
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", video_path.stem)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_index % every_n == 0:
            saved += 1
            out_path = output_dir / f"{stem}_frame_{saved:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            if max_frames is not None and max_frames > 0 and saved >= max_frames:
                break

        frame_index += 1

    cap.release()

    if saved == 0:
        return {"status": "error", "message": "error: No frames were generated with OpenCV."}

    return {
        "status": "success",
        "message": f"Extracted {saved} frame(s) with OpenCV to {output_dir}",
        "frames": saved,
        "output_dir": str(output_dir),
    }


def extract_frames(
    video_path: str,
    character: str = "Unsorted",
    interval_seconds: float = 1.0,
    max_frames: Optional[int] = None,
    output_subfolder: str = "frames",
) -> Dict:
    """
    Extract frames from a local video into:
    backend/downloads/<character>/<output_subfolder>/
    """
    try:
        src = Path(video_path).expanduser().resolve()
        if not src.exists() or not src.is_file():
            return {"status": "error", "message": f"error: Video file not found: {video_path}"}

        safe_character = _sanitize_name(character, "Unsorted")
        safe_subfolder = _sanitize_name(output_subfolder, "frames")
        out_dir = Path(__file__).resolve().parent.parent / "downloads" / safe_character / safe_subfolder
        out_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            result = _extract_with_ffmpeg(src, out_dir, interval_seconds, max_frames)
            if result.get("status") == "success":
                return result

        return _extract_with_cv2(src, out_dir, interval_seconds, max_frames)
    except Exception as exc:
        return {"status": "error", "message": f"error: {exc}"}


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Extract image frames from a local video.")
    parser.add_argument("video_path", help="Path to local video file")
    parser.add_argument("--character", default="Unsorted", help="Character folder name")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between frames")
    parser.add_argument("--max-frames", type=int, default=None, help="Optional max number of frames")
    parser.add_argument("--output-subfolder", default="frames", help="Subfolder under character downloads")
    args = parser.parse_args()

    result = extract_frames(
        video_path=args.video_path,
        character=args.character,
        interval_seconds=args.interval,
        max_frames=args.max_frames,
        output_subfolder=args.output_subfolder,
    )
    print(result.get("message", ""))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(_cli())