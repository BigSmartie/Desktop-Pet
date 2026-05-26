from langchain_core.prompts import ChatPromptTemplate

from config import settings
from core import get_llm, get_logger

logger = get_logger(__name__)


def _messages_to_text(messages: list) -> str:
    parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "").strip()
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def summarize_messages_if_needed(messages: list, existing_summary: str = "") -> str:
    """
    当消息过多时，对较早对话生成摘要。
    未开启时直接返回原摘要。
    """
    if not settings.ENABLE_SUMMARY_MEMORY:
        return existing_summary or ""

    if not messages:
        return existing_summary or ""

    max_messages = settings.MAX_CHAT_TURNS * 2
    if len(messages) <= max_messages:
        return existing_summary or ""

    old_messages = messages[:-max_messages]
    old_text = _messages_to_text(old_messages)
    if not old_text.strip():
        return existing_summary or ""

    try:
        llm = get_llm()

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个对话摘要助手。请把较早的对话内容总结成简洁、准确的中文摘要。"
                "保留：用户目标、偏好、关键事实、重要上下文、未完成事项。"
                "不要加入原对话中不存在的信息。"
            ),
            (
                "human",
                "已有摘要：\n{existing_summary}\n\n"
                "请基于下面更早的对话内容，生成新的整合摘要：\n\n{old_text}"
            ),
        ])

        chain = prompt | llm
        response = chain.invoke({
            "existing_summary": existing_summary or "无",
            "old_text": old_text,
        })

        summary = getattr(response, "content", None) or str(response)
        summary = summary.strip()

        logger.info("对话摘要生成成功")
        return summary

    except Exception:
        logger.exception("对话摘要生成失败，返回原摘要")
        return existing_summary or ""