import json
from fnmatch import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
PROFILE_FILE = DATA_DIR / "user_profile.json"
REGISTRY_FILE = DATA_DIR / "document_registry.json"
PET_STATE_FILE = DATA_DIR / "pet_state.json"

EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "dist",
    "logs",
    "local_qdrant",
    "node_modules",
    "release",
    "temp",
    "data/local_qdrant",
}
TEXT_SUFFIXES = {
    ".cjs",
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".toml",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}
WRITE_SUFFIXES = TEXT_SUFFIXES - {".env"}
WRITE_DENIED_DIRS = {
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "dist",
    "local_qdrant",
    "node_modules",
    "release",
    "data/local_qdrant",
}
PROTECTED_FILES = {
    ".env",
    "package-lock.json",
    "storage.sqlite",
}
MAX_WRITE_CHARS = 200_000
TASK_STATUSES = {"todo", "in_progress", "done"}

mcp = FastMCP("myagent-local-project")


def _safe_path(path: str) -> Path:
    candidate = (BASE_DIR / (path or ".")).resolve()
    if candidate != BASE_DIR and BASE_DIR not in candidate.parents:
        raise ValueError("Path is outside the project workspace.")
    return candidate


def _relative_parts(path: Path) -> List[str]:
    return list(path.relative_to(BASE_DIR).parts)


def _is_excluded(path: Path) -> bool:
    relative = path.relative_to(BASE_DIR).as_posix()
    parts = set(_relative_parts(path))
    return any(item in parts for item in EXCLUDED_DIRS) or relative in EXCLUDED_DIRS


def _is_write_denied(path: Path) -> bool:
    relative = path.relative_to(BASE_DIR).as_posix()
    parts = set(_relative_parts(path))
    return any(item in parts for item in WRITE_DENIED_DIRS) or relative in WRITE_DENIED_DIRS


def _safe_write_path(path: str, allow_directory: bool = False) -> Path:
    target = _safe_path(path)
    if target == BASE_DIR:
        if allow_directory:
            return target
        raise ValueError("Refusing to write to the workspace root.")

    if _is_write_denied(target):
        raise ValueError(f"Path is not writable by MCP safety policy: {path}")

    if target.name in PROTECTED_FILES:
        raise ValueError(f"Refusing to write protected file: {path}")

    if not allow_directory:
        suffix = target.suffix.lower()
        if suffix not in WRITE_SUFFIXES:
            allowed = ", ".join(sorted(WRITE_SUFFIXES))
            raise ValueError(f"Unsupported writable file type: {suffix}. Allowed: {allowed}")

    return target


def _validate_write_content(content: str) -> str:
    text = "" if content is None else str(content)
    if len(text) > MAX_WRITE_CHARS:
        raise ValueError(f"Content is too large. Maximum is {MAX_WRITE_CHARS} characters.")
    return text


def _write_result(target: Path, action: str, dry_run: bool, details: Dict[str, Any] = None) -> str:
    return _to_json({
        "action": action,
        "path": target.relative_to(BASE_DIR).as_posix(),
        "dry_run": bool(dry_run),
        **(details or {}),
    })


def _slugify(value: str) -> str:
    slug = []
    for char in (value or "").strip().lower():
        if char.isalnum():
            slug.append(char)
        elif char in {" ", "-", "_", "."}:
            slug.append("-")

    normalized = "".join(slug).strip("-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized or "untitled"


def _iter_project_files(pattern: str = "*") -> Iterable[Path]:
    normalized_pattern = pattern or "*"
    stack = [BASE_DIR]

    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name.lower(), reverse=True)
        except OSError:
            continue

        for child in children:
            if _is_excluded(child):
                continue
            if child.is_dir():
                stack.append(child)
                continue
            if not child.is_file():
                continue

            relative = child.relative_to(BASE_DIR).as_posix()
            if (
                fnmatch(child.name, normalized_pattern)
                or fnmatch(relative, normalized_pattern)
                or child.match(normalized_pattern)
            ):
                yield child


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_task(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": task.get("id"),
        "content": task.get("content", ""),
        "status": task.get("status", "todo"),
        "priority": task.get("priority", "medium"),
        "linked_goal": task.get("linked_goal"),
        "created_at": task.get("created_at", ""),
    }


@mcp.tool()
def list_project_files(pattern: str = "*", limit: int = 80) -> str:
    """List files inside the MyAgent project workspace."""
    limit = max(1, min(int(limit or 80), 300))
    matches: List[str] = []

    for path in _iter_project_files(pattern):
        matches.append(path.relative_to(BASE_DIR).as_posix())
        if len(matches) >= limit:
            break

    if not matches:
        return "No matching files."
    return "\n".join(matches)


@mcp.tool()
def read_project_file(path: str, max_chars: int = 8000) -> str:
    """Read a text file inside the MyAgent project workspace."""
    target = _safe_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not target.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if _is_excluded(target):
        raise ValueError(f"Path is excluded: {path}")

    max_chars = max(200, min(int(max_chars or 8000), 20000))
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[truncated]"
    return text


@mcp.tool()
def create_project_directory(path: str, dry_run: bool = False) -> str:
    """Create a directory inside the project workspace."""
    target = _safe_write_path(path, allow_directory=True)
    existed = target.exists()
    if existed and not target.is_dir():
        raise ValueError(f"Path exists and is not a directory: {path}")

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    return _write_result(target, "create_directory", dry_run, {
        "created": not existed,
        "existed": existed,
    })


@mcp.tool()
def create_project_file(
    path: str,
    content: str,
    overwrite: bool = False,
    create_dirs: bool = True,
    dry_run: bool = False,
) -> str:
    """Create a text file inside the project workspace, optionally overwriting it."""
    target = _safe_write_path(path)
    text = _validate_write_content(content)
    existed = target.exists()

    if existed and target.is_dir():
        raise ValueError(f"Path is a directory: {path}")
    if existed and not overwrite:
        raise ValueError(f"File already exists. Set overwrite=true to replace it: {path}")
    if not target.parent.exists() and not create_dirs:
        raise ValueError(f"Parent directory does not exist: {target.parent.relative_to(BASE_DIR).as_posix()}")

    previous_text = ""
    if existed:
        previous_text = target.read_text(encoding="utf-8", errors="replace")

    if not dry_run:
        if create_dirs:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    return _write_result(target, "create_file", dry_run, {
        "created": not existed,
        "overwritten": existed,
        "old_chars": len(previous_text),
        "new_chars": len(text),
        "changed": previous_text != text,
    })


@mcp.tool()
def append_project_file(
    path: str,
    content: str,
    create_if_missing: bool = True,
    dry_run: bool = False,
) -> str:
    """Append text to a project file, optionally creating it first."""
    target = _safe_write_path(path)
    text = _validate_write_content(content)
    existed = target.exists()

    if existed and target.is_dir():
        raise ValueError(f"Path is a directory: {path}")
    if not existed and not create_if_missing:
        raise FileNotFoundError(f"File not found: {path}")

    old_chars = 0
    if existed:
        old_chars = len(target.read_text(encoding="utf-8", errors="replace"))

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as file:
            file.write(text)

    return _write_result(target, "append_file", dry_run, {
        "created": not existed,
        "old_chars": old_chars,
        "appended_chars": len(text),
        "new_chars": old_chars + len(text),
    })


@mcp.tool()
def replace_project_file_text(
    path: str,
    old_text: str,
    new_text: str,
    expected_occurrences: int = 0,
    dry_run: bool = False,
) -> str:
    """Replace exact text inside a project text file."""
    target = _safe_write_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not target.is_file():
        raise ValueError(f"Path is not a file: {path}")

    old = _validate_write_content(old_text)
    new = _validate_write_content(new_text)
    if not old:
        raise ValueError("old_text must not be empty.")

    text = target.read_text(encoding="utf-8", errors="replace")
    count = text.count(old)
    if count == 0:
        raise ValueError("old_text was not found.")
    if expected_occurrences and count != int(expected_occurrences):
        raise ValueError(f"Expected {expected_occurrences} occurrences but found {count}.")

    updated = text.replace(old, new)
    if not dry_run:
        target.write_text(updated, encoding="utf-8")

    return _write_result(target, "replace_text", dry_run, {
        "occurrences": count,
        "old_chars": len(text),
        "new_chars": len(updated),
        "changed": text != updated,
    })


@mcp.tool()
def record_agent_note(
    title: str,
    content: str,
    category: str = "general",
    dry_run: bool = False,
) -> str:
    """Create a timestamped markdown note under data/agent_notes."""
    safe_category = _slugify(category)
    safe_title = _slugify(title)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = _safe_write_path(f"data/agent_notes/{safe_category}/{timestamp}-{safe_title}.md")
    body = _validate_write_content(content)
    note = f"# {title.strip() or 'Untitled'}\n\n{body.rstrip()}\n"

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(note, encoding="utf-8")

    return _write_result(target, "record_agent_note", dry_run, {
        "category": safe_category,
        "chars": len(note),
    })


@mcp.tool()
def create_skill_draft(
    name: str,
    description: str,
    steps: str = "",
    dry_run: bool = False,
) -> str:
    """Create a markdown draft for a reusable MyAgent skill."""
    safe_name = _slugify(name)
    target = _safe_write_path(f"skills/{safe_name}.md")
    if target.exists():
        raise ValueError(f"Skill draft already exists: skills/{safe_name}.md")

    step_lines = []
    for raw_line in (steps or "").splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if line:
            step_lines.append(f"- {line}")

    if not step_lines:
        step_lines = [
            "- Identify when this skill should be used.",
            "- Gather the required context.",
            "- Use available MCP tools to act safely.",
            "- Summarize what changed and any follow-up needed.",
        ]

    markdown = "\n".join([
        f"# {name.strip() or safe_name}",
        "",
        "## When To Use",
        description.strip() or "Describe when the assistant should use this skill.",
        "",
        "## Workflow",
        *step_lines,
        "",
        "## Tooling Notes",
        "- Prefer read-only MCP tools before write tools.",
        "- Write only inside the project workspace.",
        "- Avoid destructive actions unless the user explicitly asks.",
        "",
    ])

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")

    return _write_result(target, "create_skill_draft", dry_run, {
        "skill": safe_name,
        "chars": len(markdown),
    })


@mcp.tool()
def get_project_overview(limit: int = 80) -> str:
    """Return a compact overview of project folders, key files, and file counts."""
    limit = max(10, min(int(limit or 80), 300))
    top_level = []
    extension_counts: Dict[str, int] = {}
    sample_files: List[str] = []

    for item in sorted(BASE_DIR.iterdir(), key=lambda p: p.name.lower()):
        if item.name in EXCLUDED_DIRS:
            continue
        if _is_excluded(item):
            continue
        top_level.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
        })

    for path in _iter_project_files("*"):
        suffix = path.suffix.lower() or "[none]"
        extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
        if len(sample_files) < limit:
            sample_files.append(path.relative_to(BASE_DIR).as_posix())

    return _to_json({
        "workspace": BASE_DIR.as_posix(),
        "top_level": top_level,
        "extension_counts": dict(sorted(extension_counts.items())),
        "sample_files": sample_files,
    })


@mcp.tool()
def search_project_text(query: str, pattern: str = "*", limit: int = 30, case_sensitive: bool = False) -> str:
    """Search text files in the project workspace and return matching lines."""
    query = (query or "").strip()
    if not query:
        raise ValueError("query must not be empty.")

    limit = max(1, min(int(limit or 30), 100))
    needle = query if case_sensitive else query.lower()
    matches: List[Dict[str, Any]] = []

    for path in _iter_project_files(pattern):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            if needle not in haystack:
                continue
            matches.append({
                "path": path.relative_to(BASE_DIR).as_posix(),
                "line": line_number,
                "text": line.strip()[:500],
            })
            if len(matches) >= limit:
                return _to_json({"query": query, "matches": matches})

    return _to_json({"query": query, "matches": matches})


@mcp.tool()
def list_knowledge_documents(limit: int = 40) -> str:
    """List documents registered in the local RAG knowledge base."""
    limit = max(1, min(int(limit or 40), 200))
    records = _read_json(REGISTRY_FILE, [])
    if not isinstance(records, list):
        records = []

    return _to_json({
        "count": len(records),
        "documents": records[:limit],
    })


@mcp.tool()
def list_agent_tasks(status: str = "active", limit: int = 40) -> str:
    """List persisted assistant tasks, optionally filtered by status."""
    limit = max(1, min(int(limit or 40), 200))
    tasks = _read_json(TASKS_FILE, [])
    if not isinstance(tasks, list):
        tasks = []

    normalized_status = (status or "active").strip().lower()
    if normalized_status == "active":
        filtered = [task for task in tasks if task.get("status") != "done"]
    elif normalized_status == "all":
        filtered = tasks
    elif normalized_status in TASK_STATUSES:
        filtered = [task for task in tasks if task.get("status") == normalized_status]
    else:
        raise ValueError("status must be active, all, todo, in_progress, or done.")

    return _to_json({
        "status": normalized_status,
        "count": len(filtered),
        "tasks": [_format_task(task) for task in filtered[:limit]],
    })


@mcp.tool()
def add_agent_task(content: str, priority: str = "medium", linked_goal: str = "") -> str:
    """Add a task to the assistant task list."""
    content = (content or "").strip()
    if not content:
        raise ValueError("content must not be empty.")
    if len(content) > 500:
        raise ValueError("content is too long.")

    tasks = _read_json(TASKS_FILE, [])
    if not isinstance(tasks, list):
        tasks = []

    new_id = max([int(task.get("id", 0) or 0) for task in tasks], default=0) + 1
    task = {
        "id": new_id,
        "content": content,
        "priority": (priority or "medium").strip() or "medium",
        "status": "todo",
        "linked_goal": (linked_goal or "").strip() or None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    _write_json(TASKS_FILE, tasks)
    return _to_json({"created": _format_task(task)})


@mcp.tool()
def update_agent_task_status(task_id: int, status: str) -> str:
    """Update an assistant task status to todo, in_progress, or done."""
    normalized_status = (status or "").strip().lower()
    if normalized_status not in TASK_STATUSES:
        raise ValueError("status must be todo, in_progress, or done.")

    tasks = _read_json(TASKS_FILE, [])
    if not isinstance(tasks, list):
        tasks = []

    for task in tasks:
        if int(task.get("id", 0) or 0) == int(task_id):
            task["status"] = normalized_status
            task["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _write_json(TASKS_FILE, tasks)
            return _to_json({"updated": _format_task(task)})

    raise ValueError(f"Task not found: {task_id}")


@mcp.tool()
def get_user_profile_summary() -> str:
    """Return the persisted user profile used by the assistant."""
    profile = _read_json(PROFILE_FILE, {})
    if not isinstance(profile, dict):
        profile = {}
    visible_keys = [
        "name",
        "preferred_style",
        "interests",
        "current_projects",
        "current_goals",
        "workflow_preferences",
        "persona_notes",
        "notes",
    ]
    return _to_json({key: profile.get(key) for key in visible_keys if key in profile})


@mcp.tool()
def get_pet_snapshot() -> str:
    """Return the current persisted desktop pet state."""
    state = _read_json(PET_STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    return _to_json(state)


if __name__ == "__main__":
    mcp.run(transport="stdio")
