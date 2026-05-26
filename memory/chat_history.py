from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import settings
from core import get_logger

logger = get_logger(__name__)


def convert_messages_to_lc(messages: list) -> list:
    if not messages:
        return []

    history = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if not content or not str(content).strip():
            continue

        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))
        else:
            logger.warning("发现未知消息角色，已跳过 | role=%s", role)

    return history


def trim_messages_by_turns(messages: list, max_turns: int = None) -> list:
    """
    按最近 max_turns 轮对话裁剪消息。
    一轮按 user + assistant 近似处理。
    """
    if max_turns is None:
        max_turns = settings.MAX_CHAT_TURNS

    if not messages:
        return []

    max_messages = max_turns * 2
    return messages[-max_messages:]


def get_chat_history_for_agent(
    messages: list,
    summary: str = "",
    exclude_last_user: bool = True,
) -> list:
    if not messages:
        return []

    prepared = trim_messages_by_turns(messages)

    if exclude_last_user and prepared:
        last_msg = prepared[-1]
        if last_msg.get("role") == "user":
            prepared = prepared[:-1]

    lc_messages = convert_messages_to_lc(prepared)

    if summary and summary.strip():
        lc_messages = [
            SystemMessage(content=f"以下是更早对话的摘要，请作为上下文参考：\n{summary.strip()}")
        ] + lc_messages

    logger.info("已生成 Agent 历史消息 | count=%s", len(lc_messages))
    return lc_messages