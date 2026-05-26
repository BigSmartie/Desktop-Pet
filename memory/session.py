from core import get_logger

logger = get_logger(__name__)

# In-process session cache: session_id -> { "messages": [], "summary": "" }
_sessions = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        init_chat_session(session_id)
    return _sessions[session_id]


def init_chat_session(session_id: str = "default") -> None:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        "你好！我是你的专属 Agent。\n\n"
                        "我可以：\n"
                        "- 回答你上传的文档内容\n"
                        "- 帮你搜索公开资料\n"
                        "- 总结资料、管理知识库、查询天气\n"
                    ),
                }
            ],
            "summary": "",
        }
        logger.info(f"聊天会话已初始化: {session_id}")


def get_session_messages(session_id: str = "default") -> list:
    return get_session(session_id)["messages"]


def get_session_summary(session_id: str = "default") -> str:
    return get_session(session_id)["summary"]


def set_session_summary(summary: str, session_id: str = "default") -> None:
    get_session(session_id)["summary"] = (summary or "").strip()
    logger.info(f"已更新会话摘要: {session_id}")


def append_user_message(content: str, session_id: str = "default") -> None:
    if not content or not content.strip():
        logger.warning("append_user_message 收到空内容，已忽略")
        return

    session = get_session(session_id)
    session["messages"].append({
        "role": "user",
        "content": content.strip(),
    })
    logger.info(f"已追加用户消息: {session_id}")


def append_assistant_message(content: str, session_id: str = "default") -> None:
    if not content or not content.strip():
        logger.warning("append_assistant_message 收到空内容，已忽略")
        return

    session = get_session(session_id)
    session["messages"].append({
        "role": "assistant",
        "content": content.strip(),
    })
    logger.info(f"已追加助手消息: {session_id}")


def clear_chat_session(session_id: str = "default") -> None:
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info(f"已清空聊天会话: {session_id}")
    init_chat_session(session_id)
