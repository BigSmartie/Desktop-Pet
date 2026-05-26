import hashlib
from datetime import datetime
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


def build_document_fingerprint(file_path: str) -> str:
    """
    基于文件内容生成指纹，用于去重/更新识别。
    """
    path = Path(file_path)
    hasher = hashlib.md5()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def build_base_metadata(file_path: str, override_filename: str = None) -> dict:
    path = Path(file_path)
    fingerprint = build_document_fingerprint(file_path)
    
    # 使用原始文件名（如果提供），否则使用路径中的文件名
    display_name = override_filename or path.name

    return {
        "doc_id": fingerprint,
        "source_file": display_name,
        "source_path": str(path.resolve()),
        "source_ext": Path(display_name).suffix.lower() if override_filename else path.suffix.lower(),
        "doc_type": (Path(display_name).suffix.lower() if override_filename else path.suffix.lower()).lstrip("."),
        "ingest_time": datetime.now().isoformat(timespec="seconds"),
    }


def enrich_metadata(documents: list, file_path: str, override_filename: str = None):
    if not documents:
        logger.warning("enrich_metadata 收到空文档列表")
        return []

    base_metadata = build_base_metadata(file_path, override_filename=override_filename)

    for idx, doc in enumerate(documents):
        original_meta = doc.metadata or {}
        page = original_meta.get("page", None)
        source = original_meta.get("source", file_path)

        doc.metadata = {
            **original_meta,
            **base_metadata,
            "source": source,
            "page": page,
            "chunk_id": idx,
        }

    logger.info(
        "metadata 补充完成 | 文件=%s | doc_id=%s | chunk数=%s",
        base_metadata["source_file"],
        base_metadata["doc_id"],
        len(documents),
    )
    return documents