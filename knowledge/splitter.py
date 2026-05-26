from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    logger.info(
        "初始化文本切块器 | chunk_size=%s | chunk_overlap=%s",
        settings.CHUNK_SIZE,
        settings.CHUNK_OVERLAP,
    )

    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )


def split_documents(documents: list):
    if not documents:
        logger.warning("split_documents 收到空文档列表")
        return []

    splitter = get_text_splitter()
    splits = splitter.split_documents(documents)

    logger.info("文本切块完成 | 原始文档数=%s | 切块数=%s", len(documents), len(splits))
    return splits