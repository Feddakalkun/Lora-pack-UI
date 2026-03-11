import json
from pathlib import Path
from typing import Dict

COOKIE_PLATFORMS = ("vsco", "tiktok", "instagram")
CONFIG_PATH = Path(__file__).resolve().parent.parent / ".config" / "cookies.json"


def _normalize_value(value: str | None) -> str:
    return (value or "").strip()


def _empty_config() -> Dict[str, str]:
    return {k: "" for k in COOKIE_PLATFORMS}


def load_cookie_config() -> Dict[str, str]:
    if not CONFIG_PATH.exists():
        return _empty_config()

    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _empty_config()

    result = _empty_config()
    for key in COOKIE_PLATFORMS:
        result[key] = _normalize_value(str(payload.get(key, "")))
    return result


def save_cookie_config(values: Dict[str, str | None]) -> Dict[str, str]:
    merged = load_cookie_config()
    for key in COOKIE_PLATFORMS:
        if key in values:
            merged[key] = _normalize_value(values.get(key))

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def resolve_cookie_file(platform: str, override: str | None = None) -> str | None:
    candidate = _normalize_value(override)
    if candidate:
        p = Path(candidate)
        return str(p) if p.exists() and p.is_file() else None

    config = load_cookie_config()
    configured = _normalize_value(config.get(platform, ""))
    if not configured:
        return None

    p = Path(configured)
    return str(p) if p.exists() and p.is_file() else None


def cookie_file_state(path_value: str) -> Dict[str, str | bool]:
    value = _normalize_value(path_value)
    if not value:
        return {"path": "", "exists": False, "message": "Not set"}

    p = Path(value)
    exists = p.exists() and p.is_file()
    return {
        "path": str(p),
        "exists": bool(exists),
        "message": "File found" if exists else "File not found",
    }