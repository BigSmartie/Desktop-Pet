from pathlib import Path
from typing import List, Dict

from config import settings
from core import locked_json_path, read_json_file, write_json_atomic
from core.logger import get_logger

logger = get_logger(__name__)

REGISTRY_FILE = settings.DATA_DIR / "document_registry.json"


def load_registry() -> List[Dict]:
    if not REGISTRY_FILE.exists():
        return []

    try:
        data = read_json_file(REGISTRY_FILE)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        logger.exception("读取文档注册表失败")
        return []


def save_registry(records: List[Dict]) -> None:
    settings.ensure_dirs()
    with locked_json_path(REGISTRY_FILE):
        write_json_atomic(REGISTRY_FILE, records)


def upsert_registry_record(record: Dict) -> None:
    with locked_json_path(REGISTRY_FILE):
        records = load_registry()
        updated = False

        for i, item in enumerate(records):
            if item.get("doc_id") == record.get("doc_id"):
                records[i] = record
                updated = True
                break

        if not updated:
            records.append(record)

        write_json_atomic(REGISTRY_FILE, records)
    logger.info("文档注册表已写入 | doc_id=%s", record.get("doc_id"))


def remove_registry_record(doc_id: str) -> None:
    with locked_json_path(REGISTRY_FILE):
        records = load_registry()
        records = [r for r in records if r.get("doc_id") != doc_id]
        write_json_atomic(REGISTRY_FILE, records)
    logger.info("文档注册表已删除 | doc_id=%s", doc_id)
