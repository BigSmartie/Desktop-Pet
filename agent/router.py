from core.logger import get_logger

logger = get_logger(__name__)


def _contains_any(text: str, keywords: list) -> bool:
    text = (text or "").lower()
    return any(k.lower() in text for k in keywords)


def route_query(user_input: str) -> str:
    """
    返回一个简单路由标签：
    - weather
    - file_list
    - file_delete
    - local_summary
    - local_knowledge
    - web_search
    - general
    """
    text = (user_input or "").strip()
    if not text:
        return "general"

    weather_keywords = ["天气", "气温", "下雨", "下雪", "风力", "降水", "预报", "明天天气", "今天天气"]
    file_list_keywords = ["有哪些文档", "有哪些文件", "知识库里有什么", "列出文档", "列出文件", "我的文档"]
    file_delete_keywords = ["删除文档", "删除文件", "移除文档", "移除文件"]
    summary_keywords = ["总结", "概括", "归纳", "提炼", "摘要", "梳理重点"]
    local_keywords = ["文档", "资料", "pdf", "教材", "论文", "手册", "试卷", "知识库"]
    web_keywords = ["最新", "最近", "新闻", "公开资料", "百科", "网上", "互联网"]

    if _contains_any(text, weather_keywords):
        route = "weather"
    elif _contains_any(text, file_delete_keywords):
        route = "file_delete"
    elif _contains_any(text, file_list_keywords):
        route = "file_list"
    elif _contains_any(text, summary_keywords) and _contains_any(text, local_keywords):
        route = "local_summary"
    elif _contains_any(text, local_keywords):
        route = "local_knowledge"
    elif _contains_any(text, web_keywords):
        route = "web_search"
    else:
        route = "general"

    logger.info("查询路由结果 | route=%s | input=%s", route, text)
    return route