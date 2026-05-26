from typing import List, Dict
from core import get_llm, get_logger, get_memory_vectorstore
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_core.prompts import ChatPromptTemplate
from memory.long_term import remember_text

logger = get_logger(__name__)


def get_all_fragmented_memories() -> List[Dict]:
    """
    获取所有的事实和见解碎片，准备进行“智慧提炼”。
    """
    vectorstore = get_memory_vectorstore()
    try:
        # 获取最新的 100 条内部思考记录
        results = vectorstore.client.scroll(
            collection_name=vectorstore.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.memory_type", 
                        match=MatchValue(value="internal_thought")
                    )
                ]
            ),
            limit=100,
        )
        points, _ = results
        return [{"id": p.id, "content": p.payload.get("page_content", ""), "metadata": p.payload.get("metadata", {})} for p in points]
    except Exception:
        logger.exception("获取记忆碎片失败")
        return []


def consolidate_wisdom():
    """
    执行记忆提炼任务：将碎片化的信息聚类并形成系统的长效“智慧”。
    """
    memories = get_all_fragmented_memories()
    if not memories:
        return "当前暂无足够的记忆碎片进行提炼。"

    logger.info("开始智慧提炼任务 | 碎片总数：%s", len(memories))
    
    # 整合所有碎片文本供 Gemini 分析
    context_text = "\n---\n".join([f"[{m['metadata'].get('source', 'unknown')}] {m['content']}" for m in memories])
    
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个高级顾问和记忆官。请根据以下碎片化的对话事实和分析见解，进行【深度提炼与聚类】。\n"
            "你的任务是：\n"
            "1. 识别核心主题（如：项目进度、编码偏好、技术栈选择、长期职业规划）。\n"
            "2. 将零散的事实合并为系统化的、结构化的【长期智慧节点】。\n"
            "3. 剔除过时或冗余的信息。\n"
            "4. 输出格式应为结构清晰的 Markdown。\n"
            "输出语言：中文。"
        ),
        (
            "human",
            "待提炼的记忆素材：\n{context}"
        )
    ])

    try:
        chain = prompt | llm
        response = chain.invoke({"context": context_text})
        consolidated_content = getattr(response, "content", str(response))
        
        # 存入一条“智慧记忆”
        remember_text(
            f"### 智慧提炼报告 (Consolidated Wisdom)\n\n{consolidated_content}",
            memory_type="consolidated_wisdom",
            source="wisdom_consolidator"
        )
        
        logger.info("智慧提炼任务圆满完成。")
        return f"✅ 提炼完成！成功将 {len(memories)} 条碎片融合为结构化知识体系。"
        
    except Exception as e:
        logger.exception("智慧提炼过程出错")
        return f"❌ 提炼失败：{str(e)}"
