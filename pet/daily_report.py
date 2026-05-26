from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from config import settings
from core.logger import get_logger
from memory.tasks import load_tasks
from knowledge.registry import load_registry
from pet.companion import get_companion_summary

logger = get_logger(__name__)

REPORT_DIR = settings.DATA_DIR / "daily_reports"


def _today() -> date:
    return date.today()


def _report_path(target_date: date) -> Path:
    return REPORT_DIR / f"{target_date.isoformat()}.md"


def _active_tasks() -> List[Dict[str, Any]]:
    try:
        return [task for task in load_tasks() if task.get("status") != "done"]
    except Exception:
        logger.exception("Failed to load tasks for daily report")
        return []


def _documents() -> List[Dict[str, Any]]:
    try:
        return load_registry()
    except Exception:
        logger.exception("Failed to load documents for daily report")
        return []


def _recent_moments(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(summary.get("recent_moments") or [])[-6:]


def _tomorrow_suggestions(tasks: List[Dict[str, Any]], document_count: int, checked_in: bool) -> List[str]:
    suggestions = []
    if tasks:
        suggestions.append(f"Start with one concrete step from: {tasks[0].get('content', 'your active task')}")
    if document_count:
        suggestions.append("Ask the pet to connect tomorrow's work with one knowledge-base document.")
    if not checked_in:
        suggestions.append("Begin with a 30-second check-in so the pet can tune its reminders.")
    suggestions.append("Let the action queue collect proposed file/task changes before approving them.")
    return suggestions[:4]


def build_daily_report(target_date: date = None) -> Dict[str, Any]:
    target_date = target_date or _today()
    summary = get_companion_summary(touch=False)
    tasks = _active_tasks()
    documents = _documents()
    moments = _recent_moments(summary)
    suggestions = _tomorrow_suggestions(tasks, len(documents), summary.get("checked_in_today", False))

    lines = [
        f"# Daily Report - {target_date.isoformat()}",
        "",
        "## Companion Snapshot",
        f"- Days together: {summary.get('days_together', 1)}",
        f"- Bond level: {summary.get('level', 1)}",
        f"- Affinity: {summary.get('affinity', 0)}%",
        f"- Check-in streak: {summary.get('checkin_streak', 0)}",
        f"- Chats: {summary.get('chat_count', 0)}",
        "",
        "## Active Tasks",
    ]

    if tasks:
        for task in tasks[:8]:
            lines.append(f"- [{task.get('status', 'todo')}] {task.get('content', '')}")
    else:
        lines.append("- No active tasks recorded.")

    lines.extend([
        "",
        "## Knowledge Base",
        f"- Documents available: {len(documents)}",
    ])
    for doc in documents[:5]:
        lines.append(f"- {doc.get('source_file', 'document')} ({doc.get('chunk_count', 0)} chunks)")

    lines.extend(["", "## Recent Moments"])
    if moments:
        for moment in moments:
            lines.append(f"- {moment.get('type', 'event')}: {moment.get('detail', '')}")
    else:
        lines.append("- No recent moments yet.")

    lines.extend(["", "## Tomorrow Suggestions"])
    for item in suggestions:
        lines.append(f"- {item}")

    content = "\n".join(lines).rstrip() + "\n"
    return {
        "date": target_date.isoformat(),
        "content": content,
        "summary": {
            "active_task_count": len(tasks),
            "document_count": len(documents),
            "suggestions": suggestions,
        },
    }


def save_daily_report(target_date: date = None, force: bool = False) -> Dict[str, Any]:
    target_date = target_date or _today()
    path = _report_path(target_date)
    existed = path.exists()
    if existed and not force:
        return read_daily_report(target_date)

    report = build_daily_report(target_date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report["content"], encoding="utf-8")
    return {
        **report,
        "path": path.as_posix(),
        "exists": True,
        "created": not existed,
        "updated": existed,
    }


def read_daily_report(target_date: date = None, auto_create: bool = True) -> Dict[str, Any]:
    target_date = target_date or _today()
    path = _report_path(target_date)
    if not path.exists():
        if auto_create:
            return save_daily_report(target_date, force=True)
        report = build_daily_report(target_date)
        return {**report, "path": path.as_posix(), "exists": False, "created": False, "updated": False}

    content = path.read_text(encoding="utf-8", errors="replace")
    report = build_daily_report(target_date)
    return {
        **report,
        "content": content,
        "path": path.as_posix(),
        "exists": True,
        "created": False,
        "updated": False,
    }


def recent_daily_reports(limit: int = 7) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 7), 30))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(REPORT_DIR.glob("*.md"), reverse=True)[:limit]
    return [
        {
            "date": file.stem,
            "path": file.as_posix(),
            "size": file.stat().st_size,
            "updated_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat(timespec="seconds"),
        }
        for file in files
    ]


def reminder_status() -> Dict[str, Any]:
    summary = get_companion_summary(touch=False)
    tasks = _active_tasks()
    quiet_start = getattr(settings, "PET_QUIET_HOURS_START", "23:00")
    quiet_end = getattr(settings, "PET_QUIET_HOURS_END", "08:30")
    nudges = list(summary.get("nudges") or [])
    if tasks:
        nudges.append(f"One active task is ready to be advanced: {tasks[0].get('content', '')}")

    return {
        "enabled": bool(getattr(settings, "PET_PROACTIVE_REMINDERS", True)),
        "quiet_hours": {"start": quiet_start, "end": quiet_end},
        "next_suggestions": nudges[:4],
        "daily_report": read_daily_report(_today(), auto_create=True),
        "tomorrow_date": (_today() + timedelta(days=1)).isoformat(),
    }
