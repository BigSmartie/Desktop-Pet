from langchain_core.tools import tool
from typing import Dict, List, Optional

from core import get_logger
from memory import update_user_profile, load_user_profile

logger = get_logger(__name__)


def build_profile_tools():
    """
    构造用户画像管理工具集。
    """

    @tool
    def update_my_profile(
        name: Optional[str] = None,
        preferred_style: Optional[str] = None,
        persona_notes: Optional[str] = None,
        current_goals: Optional[List[str]] = None,
        current_projects: Optional[List[str]] = None,
        workflow_preferences: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> str:
        """
        更新我的个人画像。仅在用户明确表达“同意”、“好的”、“加入我的目标”等意愿后使用。
        
        参数说明:
        - name: 称呼
        - preferred_style: 回答偏好风格
        - persona_notes: 身份/背景描述
        - current_goals: 学习/工作目标列表
        - current_projects: 核心项目列表
        - workflow_preferences: 工作流偏好列表
        - interests: 兴趣方向列表
        - notes: 其他备注
        """
        try:
            updates = {}
            if name is not None: updates["name"] = name
            if preferred_style is not None: updates["preferred_style"] = preferred_style
            if persona_notes is not None: updates["persona_notes"] = persona_notes
            if current_goals is not None: updates["current_goals"] = current_goals
            if current_projects is not None: updates["current_projects"] = current_projects
            if workflow_preferences is not None: updates["workflow_preferences"] = workflow_preferences
            if interests is not None: updates["interests"] = interests
            if notes is not None: updates["notes"] = notes

            if not updates:
                return "未提供任何有效更新字段。"

            update_user_profile(updates)
            logger.info("用户画像工具已执行 | updates=%s", list(updates.keys()))
            return f"画像更新成功！我已经同步了以下信息：{', '.join(updates.keys())}"

        except Exception as e:
            logger.exception("更新画像工具失败")
            return f"更新画像时出错：{e}"

    return [update_my_profile]
