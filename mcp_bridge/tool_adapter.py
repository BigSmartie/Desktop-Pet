from typing import Any, Dict, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from config import settings
from core.logger import get_logger
from mcp_bridge.manager import call_mcp_tool, list_mcp_tools

logger = get_logger(__name__)


class McpToolInput(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


def _tool_name(raw_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw_name)
    return f"mcp_{safe}"


def build_mcp_tools() -> List[StructuredTool]:
    if not getattr(settings, "ENABLE_MCP", False):
        return []

    tools = []
    for tool_def in list_mcp_tools(include_disabled=False):
        raw_name = tool_def["name"]
        langchain_name = _tool_name(raw_name)
        description = tool_def.get("description") or f"MCP tool: {raw_name}"

        def make_call(target_name: str, metadata: Dict[str, Any]):
            def _call(arguments: Dict[str, Any] = None) -> str:
                if metadata.get("requires_approval"):
                    from action_queue import queue_mcp_action
                    from pet import handle_pet_event

                    action = queue_mcp_action(
                        tool_name=target_name,
                        arguments=arguments or {},
                        title=f"Approve MCP action: {metadata.get('tool') or target_name}",
                        reason=metadata.get("description", ""),
                        risk=metadata.get("risk", "medium"),
                        source="agent",
                        requires_approval=True,
                    )
                    handle_pet_event(
                        "action_queued",
                        message=f"Action waiting for approval: {metadata.get('tool') or target_name}",
                        payload={"context": {"action_id": action["id"], "risk": action["risk"]}},
                    )
                    return (
                        "Action queued for user approval. "
                        f"action_id={action['id']}, tool={target_name}, risk={action['risk']}."
                    )
                return call_mcp_tool(target_name, arguments or {})

            return _call

        tools.append(
            StructuredTool.from_function(
                func=make_call(raw_name, tool_def),
                name=langchain_name,
                description=description,
                args_schema=McpToolInput,
            )
        )

    logger.info("Built MCP tools | count=%s", len(tools))
    return tools
