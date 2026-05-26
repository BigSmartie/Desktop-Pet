from typing import Dict, List

from qdrant_client.models import Filter, FieldCondition, MatchValue

from config import settings
from core.logger import get_logger
from knowledge.loader import load_file
from knowledge.splitter import split_documents
from knowledge.metadata import enrich_metadata, build_base_metadata
from knowledge.registry import (
    load_registry,
    upsert_registry_record,
    remove_registry_record,
)

logger = get_logger(__name__)


def _find_registry_by_doc_id(doc_id: str):
    records = load_registry()
    for item in records:
        if item.get("doc_id") == doc_id:
            return item
    return None


def _delete_points_by_doc_id(vectorstore, doc_id: str) -> None:
    client = vectorstore.client
    collection_name = vectorstore.collection_name

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="metadata.doc_id",
                    match=MatchValue(value=doc_id),
                )
            ]
        ),
    )
    logger.info("已按 doc_id 删除向量 | doc_id=%s", doc_id)


def ingest_file_to_vectorstore(file_path: str, vectorstore, original_filename: str = None) -> Dict:
    """
    通用文件入库。
    """
    logger.info("开始入库文件 | file=%s | original_name=%s", file_path, original_filename)

    base_meta = build_base_metadata(file_path, override_filename=original_filename)
    doc_id = base_meta["doc_id"]
    source_file = base_meta["source_file"]

    existing = _find_registry_by_doc_id(doc_id)

    if existing and settings.ENABLE_DOC_DEDUP and not settings.ENABLE_DOC_UPDATE:
        logger.info("检测到重复文档，跳过入库 | file=%s | doc_id=%s", source_file, doc_id)
        return {
            "file_path": file_path,
            "doc_id": doc_id,
            "document_count": 0,
            "chunk_count": 0,
            "status": "skipped_duplicate",
        }

    if existing and settings.ENABLE_DOC_UPDATE:
        logger.info("检测到已存在文档，执行更新 | file=%s | doc_id=%s", source_file, doc_id)
        _delete_points_by_doc_id(vectorstore, doc_id)

    docs = load_file(file_path)
    document_count = len(docs)

    splits = split_documents(docs)
    splits = enrich_metadata(splits, file_path, override_filename=original_filename)
    chunk_count = len(splits)

    if chunk_count == 0:
        logger.warning("没有可入库的文本块 | file=%s", file_path)
        return {
            "file_path": file_path,
            "doc_id": doc_id,
            "document_count": document_count,
            "chunk_count": 0,
            "status": "empty",
        }

    vectorstore.add_documents(splits)

    record = {
        "doc_id": doc_id,
        "source_file": source_file,
        "source_path": base_meta["source_path"],
        "source_ext": base_meta["source_ext"],
        "doc_type": base_meta["doc_type"],
        "document_count": document_count,
        "chunk_count": chunk_count,
        "ingest_time": base_meta["ingest_time"],
    }
    upsert_registry_record(record)

    logger.info(
        "文件入库完成 | file=%s | doc_id=%s | document_count=%s | chunk_count=%s",
        source_file,
        doc_id,
        document_count,
        chunk_count,
    )

    return {
        "file_path": file_path,
        "doc_id": doc_id,
        "document_count": document_count,
        "chunk_count": chunk_count,
        "status": "success",
    }


def ingest_pdf_to_vectorstore(file_path: str, vectorstore) -> Dict:
    return ingest_file_to_vectorstore(file_path, vectorstore)


def delete_document_from_vectorstore(vectorstore, doc_id: str) -> Dict:
    """
    删除指定文档。
    """
    logger.info("开始删除文档 | doc_id=%s", doc_id)

    if not settings.ENABLE_DOC_DELETE:
        return {"status": "disabled", "doc_id": doc_id}

    record = _find_registry_by_doc_id(doc_id)
    if not record:
        return {"status": "not_found", "doc_id": doc_id}

    _delete_points_by_doc_id(vectorstore, doc_id)
    remove_registry_record(doc_id)

    logger.info("文档删除完成 | doc_id=%s", doc_id)
    return {"status": "deleted", "doc_id": doc_id}


def list_documents() -> List[Dict]:
    """
    返回注册表中的文档列表。
    """
    if not settings.ENABLE_DOC_LIST:
        return []

    records = load_registry()
    records = sorted(records, key=lambda x: x.get("ingest_time", ""), reverse=True)
    return records