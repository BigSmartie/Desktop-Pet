import torch

from config import settings
from core.logger import get_logger
from core.llm import get_llm
from core.embeddings import get_embeddings
from core.vectorstore import get_qdrant_client

logger = get_logger(__name__)


def check_liveness() -> dict:
    """
    基础存活检查，只确认进程本身可响应。
    """
    return {
        "status": "ok",
        "details": {
            "service": "alive",
        },
    }


def _collect_readiness_details() -> dict:
    """
    运行基础健康检查，返回一个字典结果。
    不主动请求 LLM 接口，只检查初始化层面。
    """
    result = {
        "config": {"ok": True, "detail": ""},
        "torch": {"ok": True, "detail": ""},
        "embedding": {"ok": True, "detail": ""},
        "qdrant": {"ok": True, "detail": ""},
        "llm": {"ok": True, "detail": ""},
    }

    # 配置检查
    try:
        settings.validate()
        result["config"]["detail"] = "配置校验通过"
    except Exception as e:
        result["config"] = {"ok": False, "detail": str(e)}

    # torch / cuda
    try:
        result["torch"]["detail"] = (
            f"torch={torch.__version__}, "
            f"cuda_build={torch.version.cuda}, "
            f"cuda_available={torch.cuda.is_available()}"
        )
    except Exception as e:
        result["torch"] = {"ok": False, "detail": str(e)}

    # embedding
    try:
        emb = get_embeddings()
        result["embedding"]["detail"] = f"embedding={type(emb).__name__}"
    except Exception as e:
        result["embedding"] = {"ok": False, "detail": str(e)}

    # qdrant
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        result["qdrant"]["detail"] = f"collections={len(collections)}"
    except Exception as e:
        result["qdrant"] = {"ok": False, "detail": str(e)}

    # llm
    try:
        llm = get_llm()
        result["llm"]["detail"] = f"llm={type(llm).__name__}"
    except Exception as e:
        result["llm"] = {"ok": False, "detail": str(e)}

    logger.info("健康检查完成 | result=%s", result)
    return result


def run_health_check() -> dict:
    """
    向后兼容的健康检查入口，返回组件级检查结果。
    """
    return _collect_readiness_details()


def check_readiness() -> dict:
    readiness = _collect_readiness_details()
    return {
        "status": "ok" if all(item["ok"] for item in readiness.values()) else "degraded",
        "details": readiness,
    }
