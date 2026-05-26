from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from config import settings
from core.logger import get_logger
from knowledge import retrieve_documents, format_retrieved_docs

logger = get_logger(__name__)


def build_document_summary_tool(retriever, llm):
    @tool
    def summarize_local_documents(query: str) -> str:
        """
        当用户希望总结本地知识库中的某类内容、提炼重点、生成概要时使用。
        例如：总结这份教材、提炼这篇论文重点、归纳文档内容。
        """
        try:
            if not settings.ENABLE_SUMMARY_TOOL:
                return "文档总结工具当前已禁用。"

            if not query or not query.strip():
                return "文档总结失败：query 不能为空。"

            docs = retrieve_documents(retriever, query)
            if not docs:
                return "本地知识库中没有找到可供总结的相关内容。"

            context = format_retrieved_docs(docs, max_chars_per_doc=1500)

            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "你是一个中文文档总结助手。请严格基于提供的检索内容进行总结，"
                    "不要编造检索内容之外的信息。输出尽量清晰、有层次。"
                ),
                (
                    "human",
                    "请根据以下检索内容，围绕用户需求进行总结。\n\n"
                    "【用户需求】\n{query}\n\n"
                    "【检索内容】\n{context}\n\n"
                    "请输出：\n"
                    "1. 核心内容总结\n"
                    "2. 关键要点\n"
                    "3. 若有明显局限，请说明检索内容不足之处"
                ),
            ])

            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "context": context,
            })

            content = getattr(response, "content", None) or str(response)
            return content

        except Exception as e:
            logger.exception("文档总结工具调用失败")
            return f"文档总结失败：{e}"

    return summarize_local_documents