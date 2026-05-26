from config import settings
from core import get_llm, get_logger
from agent.router import route_query
from agent.rewrite import rewrite_query_if_needed
from agent.builder import get_agent_executor_for_route
from memory import (
    load_user_profile,
    format_user_profile,
    get_context_memories,
    load_tasks,
    format_tasks_for_prompt,
)
from knowledge import list_documents

logger = get_logger(__name__)


def _build_fallback_answer(route: str, user_input: str, error: Exception) -> str:
    if not settings.ENABLE_FALLBACK_ANSWER:
        return f"Agent 执行失败：{error}"

    route_hint_map = {
        "weather": "这看起来像天气问题。你可以稍后再试，或简化地点表达。",
        "file_list": "这看起来像文档列表问题。你可以稍后再试，或检查知识库是否已有文档。",
        "file_delete": "这看起来像文档删除问题。你可以确认 doc_id 是否正确。",
        "local_summary": "这看起来像文档总结问题。你可以先确认知识库中已有相关文档。",
        "local_knowledge": "这看起来像知识库问答问题。你可以换一种更明确的问法再试。",
        "web_search": "这看起来像公开信息查询问题。你可以稍后再试，或换一个更明确的关键词。",
        "general": "你可以换个更明确的问法再试。",
    }

    hint = route_hint_map.get(route, "你可以换个更明确的问法再试。")
    return f"抱歉，这次执行失败了。\n\n问题类型：{route}\n建议：{hint}\n错误信息：{error}"


def _format_kb_status(records: list) -> str:
    if not records:
        return "当前知识库为空，用户尚未上传任何文档。"
    
    parts = [f"当前知识库共有 {len(records)} 份文档："]
    for i, r in enumerate(records, start=1):
        name = r.get("source_file", "未知文件名")
        parts.append(f"{i}. {name}")
    return "\n".join(parts)


def run_agent(agent_executor, user_input: str, chat_history: list) -> dict:
    """
    统一 Agent 执行入口。
    现在会注入用户画像与长期记忆。
    """
    text = (user_input or "").strip()
    if not text:
        return {"output": "请输入有效问题。", "image_paths": []}

    try:
        # 1. 获取增强上下文
        profile_data = load_user_profile()
        user_profile = format_user_profile(profile_data)
        
        past_memories = ""
        if settings.ENABLE_LONG_TERM_MEMORY:
            past_memories = get_context_memories(text)

        # 1.3 获取任务
        tasks = load_tasks()
        task_list = format_tasks_for_prompt(tasks, only_active=True)

        # 1.4 获取知识库状态
        kb_records = list_documents()
        kb_status = _format_kb_status(kb_records)

        # 2. 路由与改写
        route = route_query(text) if settings.ENABLE_ROUTER else "general"
        llm = get_llm()
        final_input = rewrite_query_if_needed(llm, text, route=route)

        logger.info(
            "开始执行 Agent | route=%s | original_input=%s | final_input=%s",
            route,
            text,
            final_input,
        )

        route_executor = (
            agent_executor
            if route == "general" and agent_executor is not None
            else get_agent_executor_for_route(route)
        )

        # 3. 调用 Agent
        result = route_executor.invoke({
            "input": final_input,
            "chat_history": chat_history,
            "user_profile": user_profile,
            "kb_status": kb_status,
            "past_memories": past_memories or "暂无相关历史记忆。",
            "task_list": task_list,
        })

        output = result.get("output", "")
        if not output:
            logger.warning("Agent 执行完成，但未返回 output")
            return {"output": "抱歉，我暂时没有生成有效回答。", "image_paths": []}

        # 提取中间步骤中的图片路径
        image_paths = []
        steps = result.get("intermediate_steps", [])
        for action, tool_output in steps:
            # 常见情况：RAG 工具返回 Document 列表
            if isinstance(tool_output, list):
                for item in tool_output:
                    if hasattr(item, "metadata") and item.metadata.get("image_path"):
                        path = item.metadata["image_path"]
                        if path not in image_paths:
                            image_paths.append(path)

        logger.info("Agent 执行成功 | route=%s | found_images=%s", route, len(image_paths))


        return {
            "output": output,
            "image_paths": image_paths
        }

    except Exception as e:
        logger.exception("Agent 执行失败")
        route = route_query(text) if settings.ENABLE_ROUTER else "general"
        fallback_msg = _build_fallback_answer(route, text, e)
        return {
            "output": fallback_msg,
            "image_paths": []
        }
