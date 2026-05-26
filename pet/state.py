from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config import settings
from core import locked_json_path, read_json_file, write_json_atomic
from core.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = settings.DATA_DIR / "pet_state.json"

ACTIVITY_DEFINITIONS = {
    "booting": {
        "label": "Booting",
        "description": "Starting core services.",
        "animation": "pulse",
        "tone": "neutral",
    },
    "idle": {
        "label": "Idle",
        "description": "Standing by and ready.",
        "animation": "float",
        "tone": "ready",
    },
    "listening": {
        "label": "Listening",
        "description": "Waiting for user input.",
        "animation": "listen",
        "tone": "curious",
        "default_duration_seconds": 12,
    },
    "thinking": {
        "label": "Thinking",
        "description": "Reasoning or calling tools.",
        "animation": "orbit",
        "tone": "focused",
    },
    "planning": {
        "label": "Planning",
        "description": "Preparing a safe action plan.",
        "animation": "sketch",
        "tone": "focused",
        "default_duration_seconds": 12,
    },
    "awaiting_approval": {
        "label": "Needs Approval",
        "description": "Waiting for permission before acting.",
        "animation": "hold",
        "tone": "careful",
    },
    "executing": {
        "label": "Executing",
        "description": "Running an approved action.",
        "animation": "work",
        "tone": "focused",
    },
    "celebrating": {
        "label": "Done",
        "description": "An action completed successfully.",
        "animation": "spark",
        "tone": "happy",
        "default_duration_seconds": 14,
    },
    "speaking": {
        "label": "Speaking",
        "description": "Showing the latest answer.",
        "animation": "talk",
        "tone": "engaged",
        "default_duration_seconds": 18,
    },
    "reminding": {
        "label": "Reminding",
        "description": "Delivering a reminder.",
        "animation": "alert",
        "tone": "alert",
        "default_duration_seconds": 20,
    },
    "sleeping": {
        "label": "Sleeping",
        "description": "Resting quietly.",
        "animation": "sleep",
        "tone": "calm",
    },
    "error": {
        "label": "Needs Attention",
        "description": "A service or tool failed.",
        "animation": "error",
        "tone": "worried",
    },
}

EVENT_DEFINITIONS = {
    "startup_ready": {
        "label": "Startup ready",
        "from": ["booting", "error", "idle"],
        "to": "idle",
        "mood": "ready",
        "message": "Core model is ready. MCP bridge is online.",
    },
    "startup_error": {
        "label": "Startup error",
        "from": ["booting", "idle", "thinking", "error"],
        "to": "error",
        "mood": "degraded",
        "message": "Core model startup failed. Pet and MCP APIs are still available.",
    },
    "wake": {
        "label": "Wake",
        "from": ["*"],
        "to": "idle",
        "mood": "curious",
        "message": "I am here.",
    },
    "sleep": {
        "label": "Rest",
        "from": ["idle", "speaking", "reminding", "awaiting_approval", "celebrating", "error"],
        "to": "sleeping",
        "mood": "calm",
        "message": "Resting.",
    },
    "listen": {
        "label": "Listen",
        "from": ["idle", "speaking"],
        "to": "listening",
        "mood": "curious",
        "message": "Listening.",
    },
    "chat_started": {
        "label": "Chat started",
        "from": ["*"],
        "to": "thinking",
        "mood": "focused",
        "message": "Thinking...",
    },
    "vision_received": {
        "label": "Vision received",
        "from": ["thinking", "idle", "listening"],
        "to": "thinking",
        "mood": "focused",
        "message": "Looking at the image...",
    },
    "chat_completed": {
        "label": "Chat completed",
        "from": ["thinking", "planning", "listening", "idle"],
        "to": "speaking",
        "mood": "engaged",
    },
    "tool_call_started": {
        "label": "Tool call",
        "from": ["thinking", "idle"],
        "to": "thinking",
        "mood": "focused",
        "message": "Using tools...",
    },
    "action_planned": {
        "label": "Action planned",
        "from": ["*"],
        "to": "planning",
        "mood": "focused",
        "message": "I am preparing a safe action plan.",
    },
    "action_queued": {
        "label": "Action queued",
        "from": ["*"],
        "to": "awaiting_approval",
        "mood": "careful",
        "message": "I prepared an action and need your approval.",
    },
    "action_approved": {
        "label": "Action approved",
        "from": ["awaiting_approval", "idle", "speaking"],
        "to": "planning",
        "mood": "focused",
        "message": "Permission received. Preparing to act.",
        "default_duration_seconds": 6,
    },
    "action_rejected": {
        "label": "Action rejected",
        "from": ["*"],
        "to": "idle",
        "mood": "calm",
        "message": "Action skipped.",
        "default_duration_seconds": 10,
    },
    "action_started": {
        "label": "Action started",
        "from": ["*"],
        "to": "executing",
        "mood": "focused",
        "message": "Executing approved action...",
    },
    "action_succeeded": {
        "label": "Action succeeded",
        "from": ["*"],
        "to": "celebrating",
        "mood": "happy",
        "message": "Action completed.",
    },
    "action_failed": {
        "label": "Action failed",
        "from": ["*"],
        "to": "error",
        "mood": "worried",
        "message": "Action failed.",
    },
    "reminder": {
        "label": "Reminder",
        "from": ["*"],
        "to": "reminding",
        "mood": "alert",
        "message": "You have a reminder.",
    },
    "idle": {
        "label": "Back to idle",
        "from": ["*"],
        "to": "idle",
        "mood": "ready",
        "message": "Standing by.",
    },
    "error": {
        "label": "Error",
        "from": ["*"],
        "to": "error",
        "mood": "worried",
        "message": "Something went wrong.",
    },
    "recover": {
        "label": "Recover",
        "from": ["error"],
        "to": "idle",
        "mood": "ready",
        "message": "Recovered and ready.",
    },
    "position_changed": {
        "label": "Position changed",
        "from": ["*"],
        "to": None,
    },
}

TRANSIENT_ACTIVITIES = {"listening", "speaking", "reminding", "planning", "celebrating"}

DEFAULT_STATE = {
    "activity": "booting",
    "mood": "neutral",
    "message": "Starting up.",
    "last_event": "boot",
    "updated_at": "",
    "expires_at": "",
    "position": {"x": 80, "y": 80},
    "context": {},
}


def _now_dt() -> datetime:
    return datetime.now()


def _to_iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _now() -> str:
    return _to_iso(_now_dt())


def _activity_display(activity: str) -> Dict[str, Any]:
    return ACTIVITY_DEFINITIONS.get(activity, ACTIVITY_DEFINITIONS["idle"])


def _event_allowed(event_def: Dict[str, Any], activity: str) -> bool:
    allowed_from = event_def.get("from", ["*"])
    return "*" in allowed_from or activity in allowed_from


def _allowed_events(activity: str) -> List[str]:
    return [
        event_name
        for event_name, event_def in EVENT_DEFINITIONS.items()
        if _event_allowed(event_def, activity)
    ]


def _normalize_position(position: Optional[Dict[str, Any]]) -> Dict[str, int]:
    position = position or {}
    default = DEFAULT_STATE["position"]
    return {
        "x": int(position.get("x", default["x"])),
        "y": int(position.get("y", default["y"])),
    }


def _normalize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    normalized = DEFAULT_STATE.copy()
    normalized.update(state or {})
    if normalized.get("activity") not in ACTIVITY_DEFINITIONS:
        normalized["activity"] = "idle"
    normalized["position"] = _normalize_position((state or {}).get("position"))
    normalized["context"] = dict((state or {}).get("context") or {})
    if not normalized.get("updated_at"):
        normalized["updated_at"] = _now()
    normalized.setdefault("expires_at", "")
    return _decorate_state(_apply_decay(normalized))


def _apply_decay(state: Dict[str, Any]) -> Dict[str, Any]:
    expires_at = _parse_iso(state.get("expires_at", ""))
    if (
        expires_at
        and state.get("activity") in TRANSIENT_ACTIVITIES
        and expires_at <= _now_dt()
    ):
        state = dict(state)
        state["activity"] = "idle"
        state["mood"] = "ready"
        state["message"] = "Standing by."
        state["last_event"] = "auto_idle"
        state["updated_at"] = _now()
        state["expires_at"] = ""
    return state


def _decorate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    activity = state.get("activity", "idle")
    state = dict(state)
    state["display"] = _activity_display(activity)
    state["allowed_events"] = _allowed_events(activity)
    return state


def _read_raw_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return DEFAULT_STATE.copy()

    try:
        data = read_json_file(STATE_FILE)
        if isinstance(data, dict):
            return data
    except Exception:
        logger.exception("Failed to read pet state")

    return DEFAULT_STATE.copy()


def get_pet_state() -> Dict[str, Any]:
    raw_state = _read_raw_state()
    state = _normalize_state(raw_state)
    if state.get("last_event") == "auto_idle" and raw_state.get("last_event") != "auto_idle":
        save_pet_state(state)
    return state


def save_pet_state(state: Dict[str, Any]) -> Dict[str, Any]:
    settings.ensure_dirs()
    normalized = _normalize_state(state)
    persistable = {
        key: value
        for key, value in normalized.items()
        if key not in {"display", "allowed_events"}
    }
    with locked_json_path(STATE_FILE):
        write_json_atomic(STATE_FILE, persistable)
    return normalized


def get_state_machine() -> Dict[str, Any]:
    return {
        "activities": ACTIVITY_DEFINITIONS,
        "events": EVENT_DEFINITIONS,
        "transient_activities": sorted(TRANSIENT_ACTIVITIES),
    }


def update_pet_state(
    activity: Optional[str] = None,
    mood: Optional[str] = None,
    message: Optional[str] = None,
    last_event: Optional[str] = None,
    position: Optional[Dict[str, int]] = None,
    context: Optional[Dict[str, Any]] = None,
    expires_at: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    state = get_pet_state()
    if activity is not None:
        state["activity"] = activity if activity in ACTIVITY_DEFINITIONS else "idle"
    if mood is not None:
        state["mood"] = mood
    if message is not None:
        state["message"] = message
    if last_event is not None:
        state["last_event"] = last_event
    if position is not None:
        state["position"] = _normalize_position(position)
    if context is not None:
        state["context"] = context

    if expires_at is not None:
        state["expires_at"] = expires_at
    elif duration_seconds:
        state["expires_at"] = _to_iso(_now_dt() + timedelta(seconds=max(1, int(duration_seconds))))
    elif activity not in TRANSIENT_ACTIVITIES:
        state["expires_at"] = ""

    state["updated_at"] = _now()
    return save_pet_state(state)


def handle_pet_event(
    event: str,
    activity: Optional[str] = None,
    mood: Optional[str] = None,
    message: Optional[str] = None,
    position: Optional[Dict[str, int]] = None,
    payload: Optional[Dict[str, Any]] = None,
    duration_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    event_name = (event or "idle").strip()
    event_def = EVENT_DEFINITIONS.get(event_name, {})
    payload = payload or {}
    current_state = get_pet_state()

    if event_def and not _event_allowed(event_def, current_state["activity"]):
        logger.info(
            "Pet event not allowed | event=%s | activity=%s",
            event_name,
            current_state["activity"],
        )
        return current_state

    target_activity = activity
    if target_activity is None:
        target_activity = event_def.get("to", current_state["activity"]) if event_def else current_state["activity"]
    if target_activity is None:
        target_activity = current_state["activity"]

    target_mood = mood or payload.get("mood") or event_def.get("mood") or current_state.get("mood")
    target_message = (
        message
        or payload.get("message")
        or event_def.get("message")
        or current_state.get("message")
    )

    final_duration = duration_seconds or payload.get("duration_seconds")
    if final_duration is None:
        final_duration = _activity_display(target_activity).get("default_duration_seconds")

    context = current_state.get("context", {})
    if payload.get("context"):
        context = {**context, **payload["context"]}

    return update_pet_state(
        activity=target_activity,
        mood=target_mood,
        message=target_message,
        last_event=event_name,
        position=position,
        context=context,
        duration_seconds=final_duration,
    )
