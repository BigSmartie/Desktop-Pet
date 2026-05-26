from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings
from config.app_settings import get_pet_preferences
from core import locked_json_path, read_json_file, write_json_atomic
from core.logger import get_logger

logger = get_logger(__name__)

COMPANION_FILE = settings.DATA_DIR / "companion.json"
MAX_RECENT_MOMENTS = 24
MAX_CHECKINS = 120


def _now_dt() -> datetime:
    return datetime.now()


def _now() -> str:
    return _now_dt().isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


def _default_companion() -> Dict[str, Any]:
    now = _now()
    return {
        "started_at": now,
        "last_seen_at": now,
        "interaction_count": 0,
        "chat_count": 0,
        "pet_event_count": 0,
        "checkins": [],
        "recent_moments": [],
    }


def _read_raw_companion() -> Dict[str, Any]:
    if not COMPANION_FILE.exists():
        return _default_companion()

    try:
        data = read_json_file(COMPANION_FILE)
        if isinstance(data, dict):
            return data
    except Exception:
        logger.exception("Failed to read companion profile")

    return _default_companion()


def _normalize_companion(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = _default_companion()
    normalized.update(data or {})
    normalized["interaction_count"] = int(normalized.get("interaction_count") or 0)
    normalized["chat_count"] = int(normalized.get("chat_count") or 0)
    normalized["pet_event_count"] = int(normalized.get("pet_event_count") or 0)
    normalized["checkins"] = list(normalized.get("checkins") or [])[-MAX_CHECKINS:]
    normalized["recent_moments"] = list(normalized.get("recent_moments") or [])[-MAX_RECENT_MOMENTS:]
    return normalized


def _save_companion(data: Dict[str, Any]) -> Dict[str, Any]:
    settings.ensure_dirs()
    normalized = _normalize_companion(data)
    with locked_json_path(COMPANION_FILE):
        write_json_atomic(COMPANION_FILE, normalized)
    return normalized


def _load_companion() -> Dict[str, Any]:
    return _normalize_companion(_read_raw_companion())


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _days_together(started_at: str) -> int:
    started = _parse_date(started_at) or date.today()
    return max(1, (date.today() - started).days + 1)


def _checkin_streak(checkins: List[Dict[str, Any]]) -> int:
    days = {
        item.get("date")
        for item in checkins
        if isinstance(item, dict) and item.get("date")
    }
    cursor = date.today()
    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _recent_checkin(checkins: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not checkins:
        return None
    return sorted(
        [item for item in checkins if isinstance(item, dict) and item.get("date")],
        key=lambda item: item["date"],
        reverse=True,
    )[0]


def _load_context_counts() -> Dict[str, Any]:
    active_tasks = []
    documents = []
    profile = {}

    try:
        from memory.tasks import load_tasks

        tasks = load_tasks()
        active_tasks = [task for task in tasks if task.get("status") != "done"]
    except Exception:
        logger.exception("Failed to load tasks for companion summary")

    try:
        from knowledge.registry import load_registry

        documents = load_registry()
    except Exception:
        logger.exception("Failed to load documents for companion summary")

    try:
        from memory.profile import load_user_profile

        profile = load_user_profile()
    except Exception:
        logger.exception("Failed to load profile for companion summary")

    return {
        "active_tasks": active_tasks,
        "document_count": len(documents or []),
        "profile": profile or {},
    }


def _build_greeting(
    companion: Dict[str, Any],
    active_task_count: int,
    document_count: int,
    streak_days: int,
    checked_in_today: bool,
) -> str:
    hour = _now_dt().hour
    if hour < 6:
        opening = "Still here with you."
    elif hour < 12:
        opening = "Good morning. I am ready."
    elif hour < 18:
        opening = "I am keeping watch over your workspace."
    else:
        opening = "Evening mode is on. We can wrap things gently."

    if checked_in_today:
        return f"{opening} Today's check-in is saved."
    if active_task_count:
        return f"{opening} You have {active_task_count} active task{'s' if active_task_count != 1 else ''}."
    if document_count:
        return f"{opening} Your knowledge base has {document_count} document{'s' if document_count != 1 else ''}."
    if streak_days:
        return f"{opening} Your check-in streak is {streak_days} day{'s' if streak_days != 1 else ''}."
    return opening


def _build_nudges(
    active_task_count: int,
    document_count: int,
    checked_in_today: bool,
    recent_checkin: Optional[Dict[str, Any]],
) -> List[str]:
    nudges = []
    if not checked_in_today:
        nudges.append("Leave a quick check-in so I can remember today's tone.")
    if active_task_count:
        nudges.append(f"Pick one of the {active_task_count} active tasks as today's anchor.")
    if document_count:
        nudges.append("Ask me to connect today's work with your private knowledge base.")
    if recent_checkin and recent_checkin.get("note"):
        nudges.append("I can turn your latest check-in into a small action plan.")
    return nudges[:3]


def record_companion_event(
    event_type: str,
    detail: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    companion = _load_companion()
    event_type = (event_type or "event").strip()
    detail = (detail or "").strip()

    companion["interaction_count"] += 1
    companion["last_seen_at"] = _now()
    if event_type == "chat":
        companion["chat_count"] += 1
    elif event_type.startswith("pet_"):
        companion["pet_event_count"] += 1

    moment = {
        "time": companion["last_seen_at"],
        "type": event_type,
        "detail": detail[:220],
        "metadata": metadata or {},
    }
    companion["recent_moments"] = (companion.get("recent_moments") or [])[-(MAX_RECENT_MOMENTS - 1):]
    companion["recent_moments"].append(moment)
    return _save_companion(companion)


def record_daily_check_in(mood: str = "", note: str = "") -> Dict[str, Any]:
    companion = _load_companion()
    today = _today()
    checkins = [
        item for item in companion.get("checkins", [])
        if isinstance(item, dict) and item.get("date") != today
    ]
    checkin = {
        "date": today,
        "time": _now(),
        "mood": (mood or "").strip()[:80],
        "note": (note or "").strip()[:1000],
    }

    checkins.append(checkin)
    companion["checkins"] = checkins[-MAX_CHECKINS:]
    companion["last_seen_at"] = _now()
    companion["interaction_count"] += 1
    companion["recent_moments"] = (companion.get("recent_moments") or [])[-(MAX_RECENT_MOMENTS - 1):]
    companion["recent_moments"].append({
        "time": companion["last_seen_at"],
        "type": "daily_check_in",
        "detail": checkin["note"] or checkin["mood"] or "Daily check-in saved.",
        "metadata": {"mood": checkin["mood"], "date": today},
    })
    return _save_companion(companion)


def get_companion_summary(touch: bool = True) -> Dict[str, Any]:
    companion = _load_companion()
    if touch:
        companion["last_seen_at"] = _now()
        companion = _save_companion(companion)

    context = _load_context_counts()
    active_tasks = context["active_tasks"]
    active_task_count = len(active_tasks)
    document_count = context["document_count"]
    checkins = companion.get("checkins", [])
    streak_days = _checkin_streak(checkins)
    recent_checkin = _recent_checkin(checkins)
    checked_in_today = bool(recent_checkin and recent_checkin.get("date") == _today())
    interactions = int(companion.get("interaction_count") or 0)
    level = min(12, 1 + interactions // 12 + streak_days // 3 + document_count // 10)
    affinity = min(100, 18 + interactions * 2 + streak_days * 6 + min(document_count, 20))
    pet_preferences = get_pet_preferences()

    return {
        "pet_name": pet_preferences.get("name", "Maple"),
        "pet_persona": pet_preferences.get("persona", ""),
        "pet_tone": pet_preferences.get("tone", "warm"),
        "pet_theme": pet_preferences.get("theme", "mint"),
        "started_at": companion.get("started_at", ""),
        "last_seen_at": companion.get("last_seen_at", ""),
        "days_together": _days_together(companion.get("started_at", "")),
        "interaction_count": interactions,
        "chat_count": int(companion.get("chat_count") or 0),
        "pet_event_count": int(companion.get("pet_event_count") or 0),
        "checkin_streak": streak_days,
        "checked_in_today": checked_in_today,
        "recent_checkin": recent_checkin,
        "recent_moments": list(companion.get("recent_moments") or [])[-6:],
        "active_task_count": active_task_count,
        "next_task": active_tasks[0] if active_tasks else None,
        "document_count": document_count,
        "level": level,
        "affinity": affinity,
        "greeting": _build_greeting(
            companion,
            active_task_count,
            document_count,
            streak_days,
            checked_in_today,
        ),
        "nudges": _build_nudges(
            active_task_count,
            document_count,
            checked_in_today,
            recent_checkin,
        ),
    }
