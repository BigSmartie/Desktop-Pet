from langchain_core.prompts import ChatPromptTemplate

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def rewrite_query_if_needed(llm, user_input: str, route: str = "general") -> str:
    """
    可选的查询改写。
    没开启时直接返回原问题。
    """
    text = (user_input or "").strip()
    if not text:
        return text

    if not settings.ENABLE_QUERY_REWRITE:
        return text

    try:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个查询改写助手。请将用户输入改写成更清晰、更适合检索或工具调用的一句话。"
                "不要改变原意，不要添加新事实，不要输出解释，只输出改写后的问题。"
            ),
            (
                "human",
                "请改写下面的问题，使其更适合后续检索/工具调用。\n"
                "路由类型：{route}\n"
                "原问题：{user_input}"
            ),
        ])

        chain = prompt | llm
        response = chain.invoke({
            "route": route,
            "user_input": text,
        })

        rewritten = getattr(response, "content", None) or str(response)
        rewritten = rewritten.strip()

        if rewritten:
            logger.info("查询改写成功 | before=%s | after=%s", text, rewritten)
            return rewritten

        return text

    except Exception:
        logger.exception("查询改写失败，回退原问题")
        return text