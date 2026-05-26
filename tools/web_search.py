from langchain_core.tools import tool

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def build_web_search_tool():
    """
    构造互联网搜索工具。
    """

    @tool
    def search_internet(query: str) -> str:
        """
        当需要查询公开网页资料、最新资讯、百科、新闻、实时公开信息时，使用此工具。
        """
        try:
            if not settings.ENABLE_WEB_SEARCH:
                return "互联网搜索工具当前已禁用。"

            if not query or not query.strip():
                return "互联网搜索失败：query 不能为空。"

            logger.info("调用互联网搜索工具 | query=%s", query)

            try:
                from langchain_community.tools import DuckDuckGoSearchRun
            except ImportError:
                logger.exception("导入 DuckDuckGoSearchRun 失败")
                return "互联网搜索工具不可用：缺少 langchain_community 或相关依赖。"

            try:
                search = DuckDuckGoSearchRun()
            except ImportError:
                logger.exception("初始化 DuckDuckGoSearchRun 失败")
                return "互联网搜索工具不可用：缺少依赖 ddgs，请安装：pip install -U ddgs"
            except Exception as e:
                logger.exception("初始化 DuckDuckGoSearchRun 异常")
                return f"互联网搜索工具初始化失败：{e}"

            result = search.invoke(query)

            if not result or not str(result).strip():
                return "互联网搜索未找到相关结果。"

            logger.info("互联网搜索工具调用成功")
            return str(result)

        except Exception as e:
            logger.exception("互联网搜索工具调用失败")
            return f"互联网搜索失败：{e}"

    return search_internet