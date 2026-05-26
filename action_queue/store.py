import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from core import locked_json_path, read_json_file, write_json_atomic
from core.logger import get_logger

logger = get_logger(__name__)

ACTION_QUEUE_FILE = settings.DATA_DIR / "action_queue.json"
VALID_STATUSES = {
    "pending_approval",
    "approved",
    "running",
    "succeeded",
    "failed",
    "rejected",
    "cancelled",
}
TERMINAL_STATUSES = {"succeeded", "failed", "rejected", "cancelled"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    return f"act_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _read_actions_unlocked() -> List[Dict[str, Any]]:
    if not ACTION_QUEUE_FILE.exists():
        return []

    try:
        data = read_json_file(ACTION_QUEUE_FILE)
        if isinstance(data, list):
            return [_normalize_action(item) for item in data if isinstance(item, dict)]
    except Exception:
        logger.exception("Failed to read action queue")

    return []


def _write_actions_unlocked(actions: List[Dict[str, Any]]) -> None:
    settings.ensure_dirs()
    write_json_atomic(ACTION_QUEUE_FILE, [_normalize_action(item) for item in actions])


def _normalize_action(action: Dict[str, Any]) -> Dict[str, Any]:
    now = _now()
    normalized = {
        "id": action.get("id") or _new_id(),
        "kind": action.get("kind") or "mcp_tool",
        "title": action.get("title") or "Untitled action",
        "tool_name": action.get("tool_name") or "",
        "arguments": dict(action.get("arguments") or {}),
        "risk": action.get("risk") or "medium",
        "reason": action.get("reason") or "",
        "source": action.get("source") or "agent",
        "requires_approval": bool(action.get("requires_approval", True)),
        "status": action.get("status") if action.get("status") in VALID_STATUSES else "pending_approval",
        "created_at": action.get("created_at") or now,
        "updated_at": action.get("updated_at") or now,
        "approved_at": action.get("approved_at") or "",
        "completed_at": action.get("completed_at") or "",
        "result": action.get("result") or "",
        "error": action.get("error") or "",
    }
    return normalized


def _find_action(actions: List[Dict[str, Any]], action_id: str) -> Optional[Dict[str, Any]]:
    for action in actions:
        if action.get("id") == action_id:
            return action
    return None


def list_actions(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 50), 200))
    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()

    if status:
        status = status.strip()
        actions = [action for action in actions if action.get("status") == status]

    actions.sort(key=lambda action: action.get("created_at", ""), reverse=True)
    return actions[:limit]


def get_action_queue_summary(limit: int = 50) -> Dict[str, Any]:
    actions = list_actions(limit=limit)
    counts: Dict[str, int] = {status: 0 for status in VALID_STATUSES}
    for action in actions:
        counts[action.get("status", "pending_approval")] = counts.get(action.get("status"), 0) + 1

    return {
        "actions": actions,
        "counts": counts,
        "pending_count": counts.get("pending_approval", 0),
        "running_count": counts.get("running", 0),
        "recent_count": len(actions),
    }


def queue_mcp_action(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    title: str = "",
    reason: str = "",
    risk: str = "medium",
    source: str = "agent",
    requires_approval: bool = True,
) -> Dict[str, Any]:
    tool_name = (tool_name or "").strip()
    if not tool_name:
        raise ValueError("tool_name must not be empty.")

    now = _now()
    action = _normalize_action({
        "id": _new_id(),
        "kind": "mcp_tool",
        "title": title or f"Run {tool_name}",
        "tool_name": tool_name,
        "arguments": dict(arguments or {}),
        "risk": risk or "medium",
        "reason": reason or "",
        "source": source or "agent",
        "requires_approval": requires_approval,
        "status": "pending_approval" if requires_approval else "approved",
        "created_at": now,
        "updated_at": now,
    })

    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()
        actions.append(action)
        _write_actions_unlocked(actions)

    logger.info("Action queued | id=%s | tool=%s | risk=%s", action["id"], tool_name, risk)
    return action


def approve_action(action_id: str, approved_by: str = "user") -> Dict[str, Any]:
    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()
        action = _find_action(actions, action_id)
        if not action:
            raise KeyError(f"Action not found: {action_id}")
        if action["status"] in TERMINAL_STATUSES:
            raise ValueError(f"Cannot approve a terminal action: {action['status']}")

        action["status"] = "approved"
        action["approved_at"] = _now()
        action["updated_at"] = action["approved_at"]
        action["approved_by"] = approved_by
        _write_actions_unlocked(actions)

    return action


def reject_action(action_id: str, reason: str = "") -> Dict[str, Any]:
    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()
        action = _find_action(actions, action_id)
        if not action:
            raise KeyError(f"Action not found: {action_id}")
        if action["status"] in TERMINAL_STATUSES:
            raise ValueError(f"Cannot reject a terminal action: {action['status']}")

        action["status"] = "rejected"
        action["error"] = reason or "Rejected by user."
        action["completed_at"] = _now()
        action["updated_at"] = action["completed_at"]
        _write_actions_unlocked(actions)

    return action


def _mark_action_running(action_id: str) -> Dict[str, Any]:
    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()
        action = _find_action(actions, action_id)
        if not action:
            raise KeyError(f"Action not found: {action_id}")
        if action["status"] == "pending_approval":
            raise PermissionError("Action is waiting for user approval.")
        if action["status"] in TERMINAL_STATUSES:
            raise ValueError(f"Cannot run a terminal action: {action['status']}")

        action["status"] = "running"
        action["updated_at"] = _now()
        action["error"] = ""
        _write_actions_unlocked(actions)
        return action


def _finish_action(action_id: str, status: str, result: str = "", error: str = "") -> Dict[str, Any]:
    with locked_json_path(ACTION_QUEUE_FILE):
        actions = _read_actions_unlocked()
        action = _find_action(actions, action_id)
        if not action:
            raise KeyError(f"Action not found: {action_id}")

        action["status"] = status
        action["result"] = result[:12000]
        action["error"] = error[:4000]
        action["completed_at"] = _now()
        action["updated_at"] = action["completed_at"]
        _write_actions_unlocked(actions)
        return action


async def execute_action_async(action_id: str) -> Dict[str, Any]:
    action = _mark_action_running(action_id)

    try:
        from mcp_bridge.manager import call_mcp_tool_async

        result = await call_mcp_tool_async(action["tool_name"], action["arguments"])
        failed = result.startswith("MCP tool call failed") or result.startswith("MCP tool returned an error")
        return _finish_action(
            action_id,
            status="failed" if failed else "succeeded",
            result="" if failed else result,
            error=result if failed else "",
        )
    except Exception as exc:
        logger.exception("Action execution failed | id=%s", action_id)
        return _finish_action(action_id, status="failed", error=str(exc))
