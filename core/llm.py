from langchain_ollama import ChatOllama

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def get_llm(model_name: str = None):
    """
    初始化并返回 Ollama LLM 实例。
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider != "ollama":
        logger.warning(f"当前配置的 provider 为 {provider}，但代码已切换为仅支持 ollama。")

    target_model = model_name or settings.OLLAMA_MODEL
    
    logger.info("正在初始化 Ollama LLM | model=%s | base_url=%s", target_model, settings.OLLAMA_BASE_URL)
    
    return ChatOllama(
        model=target_model,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        num_predict=settings.LLM_MAX_TOKENS,
    )