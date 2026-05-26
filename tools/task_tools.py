from langchain_core.tools import tool
from typing import Optional, Literal

from memory.tasks import add_task, update_task, delete_task, load_tasks, format_tasks_for_prompt
from core import get_logger

logger = get_logger(__name__)


def build_task_tools():
    """
    构造任务管理工具集。
    """

    @tool
    def manage_user_tasks(
        action: Literal["add", "update", "delete", "list"],
        content: Optional[str] = None,
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        linked_goal: Optional[str] = None
    ) -> str:
        """
        管理我的任务清单 (TODO List)。你可以通过此工具帮助我记录具体的行动项。
        
        参数说明:
        - action: 必填。操作类型: add (增加), update (修改), delete (删除), list (列出)。
        - content: 任务的具体内容。仅在 add 时必填，update 时可选。
        - task_id: 任务的数字 ID。在 update 或 delete 时必填。
        - status: 任务的状态。仅在 update 时有效。可选值: todo (待办), in_progress (进行中), done (已完成)。
        - linked_goal: 关联的阶段性目标名称（即画像中的 Goals）。
        """
        try:
            if action == "add":
                if not content:
                    return "错误：新增任务时必须提供具体内容 content。"
                task = add_task(content, linked_goal=linked_goal)
                return f"✅ 任务记录成功！ID: {task['id']} | 内容: {content}"

            elif action == "update":
                if not task_id:
                    return "错误：更新任务时必须提供 task_id。"
                
                updates = {}
                if status: updates["status"] = status
                if content: updates["content"] = content
                if linked_goal: updates["linked_goal"] = linked_goal
                
                if not updates:
                    return "错误：未提供任何需要更新的字段内容。"
                
                res = update_task(task_id, updates)
                if not res:
                    return f"错误：未找到 ID 为 {task_id} 的任务。"
                return f"✅ 任务 {task_id} 更新成功。"

            elif action == "delete":
                if not task_id:
                    return "错误：删除任务时必须提供 task_id。"
                if delete_task(task_id):
                    return f"✅ 任务 {task_id} 已删除。"
                return f"错误：未找到 ID 为 {task_id} 的任务。"

            elif action == "list":
                tasks = load_tasks()
                return format_tasks_for_prompt(tasks)

            return f"未知操作: {action}"

        except Exception as e:
            logger.exception("任务工具调用失败")
            return f"任务工具执行失败：{e}"

    return [manage_user_tasks]
