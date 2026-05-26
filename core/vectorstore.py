from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

from config import settings
from core.embeddings import get_embeddings
from core.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    获取 Qdrant 客户端（本地模式）。
    """
    logger.info("正在初始化 Qdrant 客户端 | path=%s", settings.QDRANT_PATH)
    client = QdrantClient(path=settings.QDRANT_PATH)
    return client


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    """
    确保指定 collection 存在。
    """
    if not client.collection_exists(collection_name):
        logger.info(
            "Qdrant collection 不存在，正在创建 | collection=%s | vector_size=%s",
            collection_name,
            settings.VECTOR_SIZE,
        )
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
    else:
        logger.info("Qdrant collection 已存在 | collection=%s", collection_name)


def _build_vectorstore(collection_name: str) -> QdrantVectorStore:
    client = get_qdrant_client()
    ensure_collection(client, collection_name)

    embeddings = get_embeddings()

    logger.info("正在初始化 VectorStore | collection=%s", collection_name)

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    return vectorstore


@lru_cache(maxsize=1)
def get_vectorstore() -> QdrantVectorStore:
    """
    主知识库向量库。
    """
    return _build_vectorstore(settings.QDRANT_COLLECTION_NAME)


@lru_cache(maxsize=1)
def get_memory_vectorstore() -> QdrantVectorStore:
    """
    长期记忆向量库。
    """
    return _build_vectorstore(settings.MEMORY_COLLECTION_NAME)