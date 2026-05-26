import os
from pathlib import Path

from langchain_community.document_loaders import PDFPlumberLoader, TextLoader

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def validate_file_path(file_path: str) -> Path:
    if not file_path:
        raise ValueError("file_path 不能为空。")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {file_path}")

    if not path.is_file():
        raise ValueError(f"目标不是文件: {file_path}")

    return path


def load_pdf(file_path: str):
    path = validate_file_path(file_path)

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"当前文件不是 PDF: {file_path}")

    logger.info("开始加载 PDF: %s", file_path)
    loader = PDFPlumberLoader(str(path))
    docs = loader.load()
    
    # OCR 增强：如果开启了 OCR，提取图片中的文字并合并
    if settings.ENABLE_OCR:
        from knowledge.ocr import extract_images_from_pdf, run_ocr_on_images
        
        images = extract_images_from_pdf(file_path)
        if images:
            logger.info("正在对 PDF 中的图片执行 OCR...")
            ocr_results = run_ocr_on_images(images)
            
            from knowledge.vision import describe_image_with_ollama
            
            for res in ocr_results:
                page_num = res["page"]
                text = res["text"]
                
                # 获取原图信息以执行视觉分析并记录路径
                img_info = next((img for img in images if img["page"] == page_num and img["index"] == res["index"]), None)
                img_bytes = img_info["bytes"] if img_info else None
                img_path = img_info["path"] if img_info else None
                visual_description = ""
                
                if img_bytes:
                    visual_description = describe_image_with_ollama(img_bytes)

                # 尝试找到对应页码的文档并将文字和描述追加进去
                target_doc = None
                for doc in docs:
                    if doc.metadata.get("page") == page_num - 1:
                        target_doc = doc
                        break
                
                content_to_append = f"\n\n[视觉分析与 OCR 内容]\n"
                if visual_description:
                    content_to_append += f"### 画面描述 (Vision Analysis):\n{visual_description}\n"
                if text:
                    content_to_append += f"### 图片文本内容 (OCR Text):\n{text}\n"

                if target_doc:
                    target_doc.page_content += content_to_append
                    # 记录该页关联的图片路径（元数据）
                    if img_path:
                        target_doc.metadata["image_path"] = img_path
                else:
                    from langchain_core.documents import Document
                    docs.append(Document(
                        page_content=content_to_append,
                        metadata={
                            "source": file_path, 
                            "page": page_num - 1, 
                            "type": "vision",
                            "image_path": img_path
                        }
                    ))
            
            logger.info("多模态 RAG 增强完成 | 注入页数=%s", len(ocr_results))

    logger.info("PDF 加载完成: %s | 页数=%s", file_path, len(docs))
    return docs


def load_text_file(file_path: str):
    path = validate_file_path(file_path)

    logger.info("开始加载文本文件: %s", file_path)
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    logger.info("文本文件加载完成: %s | 文档数=%s", file_path, len(docs))
    return docs


def load_markdown_file(file_path: str):
    return load_text_file(file_path)


def load_file(file_path: str):
    path = validate_file_path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(file_path)
    if suffix == ".txt":
        return load_text_file(file_path)
    if suffix == ".md":
        return load_markdown_file(file_path)

    raise ValueError(f"暂不支持的文件类型: {suffix}")
