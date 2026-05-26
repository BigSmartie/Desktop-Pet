from datetime import datetime
from typing import List

from langchain_core.documents import Document

from config import settings
from core import get_logger, get_memory_vectorstore

logger = get_logger(__name__)


def remember_text(text: str, memory_type: str = "general", source: str = "manual") -> dict:
    """
    将一段文本写入长期记忆向量库。
    """
    if not settings.ENABLE_LONG_TERM_MEMORY:
        return {"status": "disabled"}

    content = (text or "").strip()
    if not content:
        return {"status": "empty"}

    try:
        vectorstore = get_memory_vectorstore()

        doc = Document(
            page_content=content,
            metadata={
                "memory_type": memory_type,
                "source": source,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

        vectorstore.add_documents([doc])

        logger.info("长期记忆写入成功 | type=%s | source=%s", memory_type, source)
        return {"status": "success"}

    except Exception as e:
        logger.exception("长期记忆写入失败")
        return {"status": "error", "detail": str(e)}


def search_memory(query: str) -> List[Document]:
    """
    从长期记忆向量库检索相关记忆。
    """
    if not settings.ENABLE_LONG_TERM_MEMORY:
        return []

    text = (query or "").strip()
    if not text:
        return []

    try:
        vectorstore = get_memory_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": settings.MEMORY_TOP_K})
        docs = retriever.invoke(text)
        logger.info("长期记忆检索完成 | hit=%s", len(docs))
        return docs

    except Exception:
        logger.exception("长期记忆检索失败")
        return []


def format_memory_docs(docs: List[Document], max_chars_per_doc: int = 500) -> str:
    if not docs:
        return ""

    parts = []
    for i, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        memory_type = metadata.get("memory_type", "general")
        source = metadata.get("source", "unknown")
        created_at = metadata.get("created_at", "unknown")
        content = (doc.page_content or "").strip()[:max_chars_per_doc]

        parts.append(
            f"【记忆 {i}】\n"
            f"类型: {memory_type}\n"
            f"来源: {source}\n"
            f"时间: {created_at}\n"
            f"内容: {content}"
        )

    return "\n\n".join(parts)


def get_context_memories(query: str) -> str:
    """
    一键获取并格式化相关长期记忆。
    """
    docs = search_memory(query)
    if not docs:
        return ""
    return format_memory_docs(docs)


def reflect_on_interaction(user_input: str, assistant_output: str) -> dict:
    """
    对本次互动进行反思，提取关键事实、项目进展、见解共识等并存入长期记忆。
    """
    if not settings.ENABLE_LONG_TERM_MEMORY:
        return {"status": "disabled"}

    try:
        from langchain_core.prompts import ChatPromptTemplate
        from core import get_llm

        llm = get_llm()
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个高级记忆反思助手。你的任务是从对话中提取【关键事实】和【深度见解】。\n"
                "提取维度：\n"
                "1. **事实 (FACT)**: 用户提到的项目、目标、身份信息、偏好（如：正在做 X 项目，喜欢 Y 风格）。\n"
                "2. **见解 (INSIGHT)**: 对话中达成的共识、分析结论、Bug 根因或推导结果（如：决定采用 A 架构，因为 B 有性能瓶颈）。\n\n"
                "输出规则：\n"
                "- 以 [FACT] 或 [INSIGHT] 开头，每条占一行。\n"
                "- 尽量准确、简洁。如果没有发现值得记录的内容，输出“无”。"
            ),
            (
                "human",
                "对话内容：\n"
                "用户：{user_input}\n"
                "助手：{assistant_output}"
            ),
        ])

        chain = prompt | llm
        response = chain.invoke({
            "user_input": user_input,
            "assistant_output": assistant_output,
        })

        output_text = getattr(response, "content", None) or str(response)
        output_text = output_text.strip()

        if not output_text or output_text == "无":
            return {"status": "no_facts"}

        lines = [line.strip() for line in output_text.split("\n") if line.strip()]
        
        count = 0
        for line in lines:
            if line.startswith("[FACT]"):
                fact = line.replace("[FACT]", "").strip("- ").strip()
                remember_text(fact, memory_type="fact_extraction", source="reflection")
                count += 1
            elif line.startswith("[INSIGHT]"):
                insight = line.replace("[INSIGHT]", "").strip("- ").strip()
                # 深度见解使用 internal_thought 类型
                remember_text(insight, memory_type="internal_thought", source="reflection")
                count += 1
            elif line != "无":
                # 兼容旧格式或未标记格式
                remember_text(line, memory_type="fact_extraction", source="reflection")
                count += 1

        logger.info("反思完成 | 提取条目数：%s", count)
        return {"status": "success", "count": count}

    except Exception:
        logger.exception("反思过程失败")
        return {"status": "error"}