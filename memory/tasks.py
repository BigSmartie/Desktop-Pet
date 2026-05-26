from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from config import settings
from core import get_logger, locked_json_path, read_json_file, write_json_atomic

logger = get_logger(__name__)

TASKS_FILE = settings.DATA_DIR / "tasks.json"


def load_tasks() -> List[Dict]:
    """
    加载所有任务。
    """
    if not TASKS_FILE.exists():
        return []
    try:
        data = read_json_file(TASKS_FILE)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        logger.exception("加载任务列表失败")
        return []


def save_tasks(tasks: List[Dict]) -> None:
    """
    保存任务列表。
    """
    settings.ensure_dirs()
    try:
        with locked_json_path(TASKS_FILE):
            write_json_atomic(TASKS_FILE, tasks)
    except Exception:
        logger.exception("保存任务列表失败")


def add_task(content: str, priority: str = "medium", linked_goal: Optional[str] = None) -> Dict:
    """
    新增一个任务。
    """
    with locked_json_path(TASKS_FILE):
        tasks = load_tasks()
        new_id = (max([t.get("id", 0) for t in tasks]) + 1) if tasks else 1
        new_task = {
            "id": new_id,
            "content": content,
            "priority": priority,
            "status": "todo",  # todo, in_progress, done
            "linked_goal": linked_goal,
            "created_at": datetime.now().isoformat()
        }
        tasks.append(new_task)
        write_json_atomic(TASKS_FILE, tasks)
    logger.info("任务已添加 | id=%s | content=%s", new_id, content)
    return new_task


def update_task(task_id: int, updates: Dict) -> Optional[Dict]:
    """
    更新任务信息或状态。
    """
    with locked_json_path(TASKS_FILE):
        tasks = load_tasks()
        for task in tasks:
            if task.get("id") == task_id:
                # 过滤掉 id，防止篡改
                updates.pop("id", None)
                task.update(updates)
                write_json_atomic(TASKS_FILE, tasks)
                logger.info("任务已更新 | id=%s | updates=%s", task_id, updates)
                return task
    return None


def delete_task(task_id: int) -> bool:
    """
    删除任务。
    """
    with locked_json_path(TASKS_FILE):
        tasks = load_tasks()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get("id") != task_id]
        if len(tasks) < original_len:
            write_json_atomic(TASKS_FILE, tasks)
            logger.info("任务已删除 | id=%s", task_id)
            return True
    return False


def format_tasks_for_prompt(tasks: List[Dict], only_active: bool = False) -> str:
    """
    将任务列表格式化为 Agent 可阅读的文本。
    """
    if not tasks:
        return "当前任务清单为空。"

    display_tasks = tasks
    if only_active:
        display_tasks = [t for t in tasks if t["status"] != "done"]

    if not display_tasks:
        return "目前没有进行中的任务。"

    lines = ["### 我的任务清单"]
    for t in display_tasks:
        status_map = {
            "todo": "⭕ 待办",
            "in_progress": "⏳ 进行中",
            "done": "✅ 已完成"
        }
        status_str = status_map.get(t["status"], t["status"])
        goal_hint = f" (关联目标: {t['linked_goal']})" if t.get("linked_goal") else ""
        lines.append(f"{t['id']}. [{status_str}] {t['content']}{goal_hint}")

    return "\n".join(lines)
