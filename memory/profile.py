from pathlib import Path
from typing import Dict

from config import settings
from core import get_logger, locked_json_path, read_json_file, write_json_atomic

logger = get_logger(__name__)

PROFILE_FILE = settings.DATA_DIR / "user_profile.json"
DEFAULT_PROFILE = {
    "name": "",
    "preferred_style": "简洁",
    "interests": [],
    "current_projects": [],
    "current_goals": [],
    "workflow_preferences": [],
    "persona_notes": "",
    "notes": "",
}


def load_user_profile() -> Dict:
    if not PROFILE_FILE.exists():
        return DEFAULT_PROFILE.copy()

    try:
        data = read_json_file(PROFILE_FILE)
        if not isinstance(data, dict):
            return DEFAULT_PROFILE.copy()

        for k, v in DEFAULT_PROFILE.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        logger.exception("读取用户画像失败，返回默认画像")
        return DEFAULT_PROFILE.copy()


def save_user_profile(profile: Dict) -> None:
    settings.ensure_dirs()
    with locked_json_path(PROFILE_FILE):
        write_json_atomic(PROFILE_FILE, profile)
    logger.info("用户画像已保存")


def update_user_profile(updates: Dict) -> Dict:
    with locked_json_path(PROFILE_FILE):
        profile = load_user_profile()
        profile.update(updates or {})
        write_json_atomic(PROFILE_FILE, profile)
    logger.info("用户画像已更新 | keys=%s", list((updates or {}).keys()))
    return profile


def format_user_profile(profile: Dict) -> str:
    """
    将用户画像格式化为供 LLM 阅读的 Context。
    """
    if not profile:
        return "用户画像信息不足。"

    lines = []
    if profile.get("name"):
        lines.append(f"- 称呼: {profile['name']}")
    if profile.get("preferred_style"):
        lines.append(f"- 偏好回答风格: {profile['preferred_style']}")
    if profile.get("persona_notes"):
        lines.append(f"- 用户身份/背景: {profile['persona_notes']}")
    
    interests = profile.get("interests", [])
    if interests:
        lines.append(f"- 兴趣领域: {', '.join(interests)}")
        
    projects = profile.get("current_projects", [])
    if projects:
        lines.append(f"- 当前核心项目: {', '.join(projects)}")
        
    goals = profile.get("current_goals", [])
    if goals:
        lines.append(f"- 当前学习/工作目标: {', '.join(goals)}")
        
    prefs = profile.get("workflow_preferences", [])
    if prefs:
        lines.append(f"- 工作流偏好: {', '.join(prefs)}")
        
    if profile.get("notes"):
        lines.append(f"- 其他备注: {profile['notes']}")

    if not lines:
        return "暂无详细用户画像信息。"

    return "\n".join(lines)
