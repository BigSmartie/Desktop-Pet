from functools import lru_cache

from langchain_classic.agents import create_react_agent, AgentExecutor

from config import settings
from core import get_llm, get_logger, get_vectorstore
from knowledge import get_retriever
from tools import (
    build_local_search_tool,
    build_web_search_tool,
    build_list_documents_tool,
    build_delete_document_tool,
    build_document_summary_tool,
    build_weather_tool,
    build_profile_tools,
    build_task_tools,
    build_thought_tools,
    build_research_tools,
)
from mcp_bridge import build_mcp_tools
from agent.prompts import get_agent_prompt

logger = get_logger(__name__)


def _resolve_retriever(retriever):
    if retriever is not None:
        return retriever
    vectorstore = get_vectorstore()
    return get_retriever(vectorstore)


def _build_tools_for_route(route: str, retriever, llm):
    vectorstore = get_vectorstore()

    tools = [
        build_local_search_tool(retriever),
    ]
    tools.extend(build_profile_tools())
    tools.extend(build_task_tools())
    tools.extend(build_thought_tools())

    if settings.ENABLE_FILE_TOOL and route in {"general", "local_knowledge", "local_summary", "file_list", "file_delete"}:
        tools.append(build_list_documents_tool())
        if route in {"general", "local_knowledge", "file_delete"}:
            tools.append(build_delete_document_tool(vectorstore))

    if settings.ENABLE_SUMMARY_TOOL and route in {"general", "local_knowledge", "local_summary"}:
        tools.append(build_document_summary_tool(retriever, llm))

    if settings.ENABLE_WEB_SEARCH and route in {"general", "web_search"}:
        tools.append(build_web_search_tool())
        tools.extend(build_research_tools())

    if settings.ENABLE_WEATHER_TOOL and route in {"general", "weather"}:
        tools.append(build_weather_tool())

    if settings.ENABLE_MCP and route in {"general", "web_search", "local_knowledge"}:
        tools.extend(build_mcp_tools())

    return tools


def build_agent_executor(retriever=None, route: str = "general") -> AgentExecutor:
    logger.info("开始构建 AgentExecutor | route=%s", route)

    llm = get_llm()
    retriever = _resolve_retriever(retriever)
    tools = _build_tools_for_route(route, retriever, llm)

    prompt = get_agent_prompt()

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=settings.AGENT_VERBOSE,
        handle_parsing_errors=True,
        return_intermediate_steps=True, # 允许捕获中间步骤中的图片元数据
    )

    logger.info("AgentExecutor 构建完成 | route=%s | tool_count=%s", route, len(tools))
    return agent_executor


@lru_cache(maxsize=8)
def get_agent_executor_for_route(route: str = "general") -> AgentExecutor:
    """
    按路由缓存的 AgentExecutor。
    """
    return build_agent_executor(route=route)
