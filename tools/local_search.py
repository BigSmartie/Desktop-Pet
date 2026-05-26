from langchain_core.tools import tool

from core.logger import get_logger
from knowledge import retrieve_documents, format_retrieved_docs

logger = get_logger(__name__)


def build_local_search_tool(retriever):
    """
    构造本地知识库检索工具。
    """

    @tool
    def search_local_knowledge(query: str) -> str:
        """
        当问题涉及用户上传的 PDF、私有资料、文档内容、教材、论文、手册时，使用此工具。
        """
        try:
            if not query or not query.strip():
                return "本地知识库检索失败：query 不能为空。"

            logger.info("调用本地知识库工具 | query=%s", query)

            docs = retrieve_documents(retriever, query)
            result = format_retrieved_docs(docs, max_chars_per_doc=1200)

            logger.info("本地知识库工具执行完成 | hit=%s", len(docs))
            return result

        except Exception as e:
            logger.exception("本地知识库工具调用失败")
            return f"本地知识库检索失败：{e}"

    return search_local_knowledge