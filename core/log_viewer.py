from pathlib import Path
from typing import Dict, List

from config import settings


def _tail_file(path: Path, max_lines: int) -> List[str]:
    if not path.exists() or not path.is_file():
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    return text.splitlines()[-max_lines:]


def read_recent_logs(max_lines: int = 160) -> Dict[str, List[str]]:
    max_lines = max(20, min(int(max_lines or 160), 1000))
    return {
        "app": _tail_file(settings.LOG_DIR / "app.log", max_lines),
        "electron_backend": _tail_file(settings.LOG_DIR / "electron-backend.log", max_lines),
    }
