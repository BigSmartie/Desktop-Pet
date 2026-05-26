import os
from functools import lru_cache

import torch
from langchain_huggingface import HuggingFaceEmbeddings

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def _resolve_device() -> str:
    """
    自动解析最终使用的 embedding 设备。
    """
    device = (settings.EMBEDDING_DEVICE or "cpu").strip().lower()

    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("检测到配置为 cuda，但当前 CUDA 不可用，自动降级为 cpu")
        return "cpu"

    return device


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    初始化并返回 Embedding 模型实例。
    """
    device = _resolve_device()

    logger.info(
        "正在初始化 Embedding 模型 | model=%s | device=%s",
        settings.EMBEDDING_MODEL_NAME,
        device,
    )

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": settings.EMBEDDING_NORMALIZE},
    )

    return embeddings