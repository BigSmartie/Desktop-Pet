from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def extract_images_from_pdf(file_path: str):
    """
    使用 PyMuPDF (fitz) 从 PDF 中提取所有图片。
    """
    if not settings.ENABLE_IMAGE_EXTRACTION:
        return []

    try:
        import fitz
        import hashlib
        doc = fitz.open(file_path)
        images = []
        settings.ensure_dirs()
        
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                
                # 生成唯一文件名防止重复存储
                file_hash = hashlib.md5(image_bytes).hexdigest()
                filename = f"{file_hash}.{ext}"
                save_path = settings.IMAGE_DIR / filename
                
                if not save_path.exists():
                    with open(save_path, "wb") as f:
                        f.write(image_bytes)
                
                images.append({
                    "bytes": image_bytes,
                    "path": str(save_path),
                    "filename": filename,
                    "page": page_index + 1,
                    "index": img_index
                })
        doc.close()
        logger.info("图片持久化完成 | file=%s | count=%s", file_path, len(images))
        return images
    except Exception:
        logger.exception("提取 PDF 图片失败 | file=%s", file_path)
        return []


def run_ocr_on_images(images: list):
    """
    使用 RapidOCR 对提取的图片进行 OCR 识别。
    """
    if not settings.ENABLE_OCR or not images:
        return []

    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        results = []
        
        for img_info in images:
            # result 格式: [[box, text, score], ...]
            result, elapsed = engine(img_info["bytes"])
            if result:
                text = "\n".join([line[1] for line in result])
                results.append({
                    "text": text,
                    "page": img_info["page"],
                    "index": img_info["index"]
                })
        
        logger.info("OCR 识别完成 | image_count=%s | result_count=%s", len(images), len(results))
        return results
    except Exception:
        logger.exception("OCR 识别过程失败")
        return []