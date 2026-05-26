import base64
from langchain_core.messages import HumanMessage

from config import settings
from core import get_llm, get_logger

logger = get_logger(__name__)


def describe_image_with_ollama(image_bytes: bytes) -> str:
    """
    使用本地 Ollama (模型: qwen3-vl:8b) 对图片内容进行深度语义描述。
    """
    try:
        # 1. 编码图片为 base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt_text = (
            "你是一个专业的视觉分析专家。请详细描述这张图片的内容。\n"
            "如果是架构图或流程图，请解释其逻辑和组件。\n"
            "如果是数据图表，请说明核心趋势和数据点。\n"
            "如果是截图或手机界面，请提取里面所有的关键文字信息和意思。\n"
            "请直接输出描述内容，使用中文。"
        )

        # 2. 初始化视觉模型
        # 注意：这里强制使用 settings.OLLAMA_VISION_MODEL
        vision_llm = get_llm(model_name=settings.OLLAMA_VISION_MODEL)

        logger.info("正在调用 Ollama (%s) 进行视觉分析...", settings.OLLAMA_VISION_MODEL)
        
        # 3. 构造消息内容
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image_b64}",
                },
            ]
        )

        # 4. 调用模型
        resp = vision_llm.invoke([message])
        
        description = resp.content
        logger.info("视觉分析已完成。")
        
        return description.strip()

    except Exception:
        logger.exception("Ollama 视觉分析调用失败")
        return "（视觉分析失败，请检查 Ollama 服务状态或模型是否已下载）"
