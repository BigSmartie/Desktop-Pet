from langchain_core.tools import tool

from config import settings
from core.logger import get_logger
from knowledge import list_documents, delete_document_from_vectorstore

logger = get_logger(__name__)


def build_list_documents_tool():
    @tool
    def list_local_documents(_: str = "") -> str:
        """
        列出当前知识库中已入库的文档。
        当用户询问“我上传了哪些文档”“知识库里有哪些文件”时使用。
        """
        try:
            if not settings.ENABLE_FILE_TOOL:
                return "文件管理工具当前已禁用。"

            records = list_documents()
            if not records:
                return "当前知识库中还没有已登记文档。"

            parts = []
            for i, item in enumerate(records, start=1):
                parts.append(
                    f"【文档 {i}】\n"
                    f"文件名: {item.get('source_file', '未知')}\n"
                    f"doc_id: {item.get('doc_id', '未知')}\n"
                    f"类型: {item.get('doc_type', '未知')}\n"
                    f"页数/文档数: {item.get('document_count', '未知')}\n"
                    f"文本块数: {item.get('chunk_count', '未知')}\n"
                    f"入库时间: {item.get('ingest_time', '未知')}"
                )

            return "\n\n".join(parts)

        except Exception as e:
            logger.exception("列出文档工具调用失败")
            return f"列出文档失败：{e}"

    return list_local_documents


def build_delete_document_tool(vectorstore):
    @tool
    def delete_local_document(doc_id: str) -> str:
        """
        删除知识库中的某个文档。输入必须是文档的 doc_id。
        当用户明确要求删除某份已入库文档时使用。
        """
        try:
            if not settings.ENABLE_FILE_TOOL:
                return "文件管理工具当前已禁用。"

            if not doc_id or not doc_id.strip():
                return "删除文档失败：doc_id 不能为空。"

            result = delete_document_from_vectorstore(vectorstore, doc_id.strip())
            status = result.get("status")

            if status == "deleted":
                return f"文档删除成功，doc_id={doc_id}"
            if status == "not_found":
                return f"未找到对应文档，doc_id={doc_id}"
            if status == "disabled":
                return "删除文档功能当前已禁用。"

            return f"删除文档结果未知：{result}"

        except Exception as e:
            logger.exception("删除文档工具调用失败")
            return f"删除文档失败：{e}"

    return delete_local_document