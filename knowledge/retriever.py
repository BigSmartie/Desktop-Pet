from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def get_retriever(vectorstore):
    """
    返回基础 Retriever。
    默认优先使用 MMR。
    """
    if settings.ENABLE_MMR:
        logger.info(
            "初始化 Retriever | mode=mmr | top_k=%s | fetch_k=%s | lambda=%s",
            settings.RETRIEVER_TOP_K,
            settings.MMR_FETCH_K,
            settings.MMR_LAMBDA_MULT,
        )
        return vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.RETRIEVER_TOP_K,
                "fetch_k": settings.MMR_FETCH_K,
                "lambda_mult": settings.MMR_LAMBDA_MULT,
            },
        )

    logger.info("初始化 Retriever | mode=similarity | top_k=%s", settings.RETRIEVER_TOP_K)
    return vectorstore.as_retriever(
        search_kwargs={"k": settings.RETRIEVER_TOP_K}
    )


def retrieve_documents(retriever, query: str):
    if not query or not query.strip():
        raise ValueError("query 不能为空。")

    logger.info("开始执行检索 | query=%s", query)
    docs = retriever.invoke(query)
    logger.info("检索完成 | hit=%s", len(docs))
    return docs


def format_retrieved_docs(docs: list, max_chars_per_doc: int = 1000) -> str:
    if not docs:
        return "本地知识库中没有找到相关内容。"

    parts = []

    for i, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        source_file = metadata.get("source_file", "未知文件")
        page = metadata.get("page", "未知页")
        chunk_id = metadata.get("chunk_id", "未知块")

        content = (doc.page_content or "").strip()
        if max_chars_per_doc > 0:
            content = content[:max_chars_per_doc]

        parts.append(
            f"【结果 {i}】\n"
            f"来源文件: {source_file}\n"
            f"页码: {page}\n"
            f"文本块ID: {chunk_id}\n"
            f"内容:\n{content}"
        )

    return "\n\n".join(parts)