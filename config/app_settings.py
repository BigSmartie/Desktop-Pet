from copy import deepcopy
from typing import Any, Dict

from .settings import settings
from core import locked_json_path, read_json_file, write_json_atomic
from core.logger import get_logger

logger = get_logger(__name__)

APP_SETTINGS_FILE = settings.DATA_DIR / "app_settings.json"
MCP_CONFIG_FILE = settings.MCP_CONFIG_PATH


def _default_app_settings() -> Dict[str, Any]:
    return {
        "model": {
            "llm_provider": settings.LLM_PROVIDER,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "ollama_model": settings.OLLAMA_MODEL,
            "ollama_vision_model": settings.OLLAMA_VISION_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "embedding_model_name": settings.EMBEDDING_MODEL_NAME,
            "embedding_device": settings.EMBEDDING_DEVICE,
            "restart_recommended": True,
        },
        "knowledge": {
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "retriever_top_k": settings.RETRIEVER_TOP_K,
            "enable_mmr": settings.ENABLE_MMR,
            "mmr_fetch_k": settings.MMR_FETCH_K,
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        },
        "pet": {
            "name": "Maple",
            "persona": "A careful local desktop companion who helps plan, remember, and act with permission.",
            "tone": "warm",
            "proactive_reminders": True,
            "daily_report_auto": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "08:30",
            "theme": "mint",
        },
    }


def _merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (updates or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_saved_app_settings() -> Dict[str, Any]:
    if not APP_SETTINGS_FILE.exists():
        return {}
    try:
        data = read_json_file(APP_SETTINGS_FILE)
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.exception("Failed to read app settings")
        return {}


def _load_mcp_config() -> Dict[str, Any]:
    try:
        data = read_json_file(MCP_CONFIG_FILE)
        return data if isinstance(data, dict) else {"servers": []}
    except Exception:
        logger.exception("Failed to read MCP config")
        return {"servers": []}


def _sanitize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _sanitize_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _sanitize_app_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    defaults = _default_app_settings()
    merged = _merge(defaults, data or {})
    model = merged["model"]
    knowledge = merged["knowledge"]
    pet = merged["pet"]

    model["llm_provider"] = "ollama"
    model["ollama_base_url"] = str(model.get("ollama_base_url") or defaults["model"]["ollama_base_url"]).strip()
    model["ollama_model"] = str(model.get("ollama_model") or defaults["model"]["ollama_model"]).strip()
    model["ollama_vision_model"] = str(model.get("ollama_vision_model") or defaults["model"]["ollama_vision_model"]).strip()
    model["temperature"] = _sanitize_float(model.get("temperature"), defaults["model"]["temperature"], 0, 2)
    model["max_tokens"] = _sanitize_int(model.get("max_tokens"), defaults["model"]["max_tokens"], 128, 8192)
    model["embedding_model_name"] = str(model.get("embedding_model_name") or defaults["model"]["embedding_model_name"]).strip()
    model["embedding_device"] = str(model.get("embedding_device") or defaults["model"]["embedding_device"]).strip().lower()
    if model["embedding_device"] not in {"cpu", "cuda"}:
        model["embedding_device"] = "cpu"
    model["restart_recommended"] = True

    knowledge["chunk_size"] = _sanitize_int(knowledge.get("chunk_size"), defaults["knowledge"]["chunk_size"], 100, 4000)
    knowledge["chunk_overlap"] = _sanitize_int(knowledge.get("chunk_overlap"), defaults["knowledge"]["chunk_overlap"], 0, 1000)
    knowledge["retriever_top_k"] = _sanitize_int(knowledge.get("retriever_top_k"), defaults["knowledge"]["retriever_top_k"], 1, 20)
    knowledge["enable_mmr"] = _sanitize_bool(knowledge.get("enable_mmr"), defaults["knowledge"]["enable_mmr"])
    knowledge["mmr_fetch_k"] = _sanitize_int(knowledge.get("mmr_fetch_k"), defaults["knowledge"]["mmr_fetch_k"], 1, 80)
    knowledge["max_file_size_mb"] = _sanitize_int(knowledge.get("max_file_size_mb"), defaults["knowledge"]["max_file_size_mb"], 1, 500)

    pet["name"] = str(pet.get("name") or defaults["pet"]["name"]).strip()[:40]
    pet["persona"] = str(pet.get("persona") or defaults["pet"]["persona"]).strip()[:800]
    pet["tone"] = str(pet.get("tone") or defaults["pet"]["tone"]).strip()[:40]
    pet["proactive_reminders"] = _sanitize_bool(pet.get("proactive_reminders"), defaults["pet"]["proactive_reminders"])
    pet["daily_report_auto"] = _sanitize_bool(pet.get("daily_report_auto"), defaults["pet"]["daily_report_auto"])
    pet["quiet_hours_start"] = str(pet.get("quiet_hours_start") or defaults["pet"]["quiet_hours_start"]).strip()[:5]
    pet["quiet_hours_end"] = str(pet.get("quiet_hours_end") or defaults["pet"]["quiet_hours_end"]).strip()[:5]
    pet["theme"] = str(pet.get("theme") or defaults["pet"]["theme"]).strip()[:40]

    return merged


def _apply_runtime_settings(app_settings: Dict[str, Any]) -> None:
    model = app_settings["model"]
    knowledge = app_settings["knowledge"]
    pet = app_settings["pet"]

    settings.OLLAMA_BASE_URL = model["ollama_base_url"]
    settings.OLLAMA_MODEL = model["ollama_model"]
    settings.OLLAMA_VISION_MODEL = model["ollama_vision_model"]
    settings.LLM_TEMPERATURE = model["temperature"]
    settings.LLM_MAX_TOKENS = model["max_tokens"]
    settings.EMBEDDING_MODEL_NAME = model["embedding_model_name"]
    settings.EMBEDDING_DEVICE = model["embedding_device"]

    settings.CHUNK_SIZE = knowledge["chunk_size"]
    settings.CHUNK_OVERLAP = knowledge["chunk_overlap"]
    settings.RETRIEVER_TOP_K = knowledge["retriever_top_k"]
    settings.ENABLE_MMR = knowledge["enable_mmr"]
    settings.MMR_FETCH_K = knowledge["mmr_fetch_k"]
    settings.MAX_FILE_SIZE_MB = knowledge["max_file_size_mb"]

    settings.ENABLE_SETTINGS_PANEL = True
    settings.PET_NAME = pet["name"]
    settings.PET_PERSONA = pet["persona"]
    settings.PET_TONE = pet["tone"]
    settings.PET_PROACTIVE_REMINDERS = pet["proactive_reminders"]
    settings.PET_DAILY_REPORT_AUTO = pet["daily_report_auto"]
    settings.PET_QUIET_HOURS_START = pet["quiet_hours_start"]
    settings.PET_QUIET_HOURS_END = pet["quiet_hours_end"]
    settings.PET_THEME = pet["theme"]


def load_app_settings() -> Dict[str, Any]:
    app_settings = _sanitize_app_settings(_load_saved_app_settings())
    _apply_runtime_settings(app_settings)
    return {
        **app_settings,
        "mcp": _load_mcp_config(),
    }


def save_app_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = _sanitize_app_settings(_load_saved_app_settings())
    updates = {key: value for key, value in (payload or {}).items() if key in {"model", "knowledge", "pet"}}
    updated = _sanitize_app_settings(_merge(current, updates))

    settings.ensure_dirs()
    with locked_json_path(APP_SETTINGS_FILE):
        write_json_atomic(APP_SETTINGS_FILE, updated)
    _apply_runtime_settings(updated)

    if isinstance((payload or {}).get("mcp"), dict):
        with locked_json_path(MCP_CONFIG_FILE):
            write_json_atomic(MCP_CONFIG_FILE, payload["mcp"])
        try:
            from mcp_bridge import reload_mcp_config

            reload_mcp_config()
        except Exception:
            logger.exception("Failed to reload MCP config after settings save")

    return load_app_settings()


def get_pet_preferences() -> Dict[str, Any]:
    return load_app_settings()["pet"]
