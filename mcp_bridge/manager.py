import asyncio
import importlib.util
import threading
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from core import read_json_file
from core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG = {
    "servers": [
        {
            "name": "local_project",
            "enabled": True,
            "transport": "stdio",
            "command": "D:/MiniConda/envs/myagent/python.exe",
            "args": ["-m", "mcp_bridge.servers.local_project"],
            "cwd": str(settings.BASE_DIR),
            "tools": [
                {
                    "name": "list_project_files",
                    "description": "List files inside the current project workspace.",
                    "enabled": True,
                },
                {
                    "name": "read_project_file",
                    "description": "Read a text file inside the current project workspace.",
                    "enabled": True,
                },
            ],
        }
    ]
}


def _sdk_available() -> bool:
    return importlib.util.find_spec("mcp") is not None


@lru_cache(maxsize=1)
def load_mcp_config() -> Dict[str, Any]:
    config_path = getattr(settings, "MCP_CONFIG_PATH", settings.BASE_DIR / "config" / "mcp_servers.json")
    try:
        if config_path.exists():
            data = read_json_file(config_path)
            if isinstance(data, dict):
                return data
    except Exception:
        logger.exception("Failed to load MCP config")
    return DEFAULT_CONFIG


def reload_mcp_config() -> Dict[str, Any]:
    load_mcp_config.cache_clear()
    return get_mcp_status()


def list_mcp_servers() -> List[Dict[str, Any]]:
    return load_mcp_config().get("servers", [])


def _iter_configured_tools(include_disabled: bool = True) -> List[Dict[str, Any]]:
    tools = []
    for server in list_mcp_servers():
        server_name = server.get("name")
        server_enabled = bool(server.get("enabled", False))
        for tool_def in server.get("tools", []):
            tool_enabled = bool(tool_def.get("enabled", server_enabled))
            if not include_disabled and (not server_enabled or not tool_enabled):
                continue
            tools.append(
                {
                    "name": f"{server_name}__{tool_def.get('name')}",
                    "server": server_name,
                    "tool": tool_def.get("name"),
                    "description": tool_def.get("description", ""),
                    "enabled": server_enabled and tool_enabled,
                    "requires_approval": bool(tool_def.get("requires_approval", False)),
                    "risk": tool_def.get("risk", "low"),
                }
            )
    return tools


def list_mcp_tools(include_disabled: bool = True) -> List[Dict[str, Any]]:
    return _iter_configured_tools(include_disabled=include_disabled)


def get_mcp_status() -> Dict[str, Any]:
    servers = list_mcp_servers()
    return {
        "enabled": bool(getattr(settings, "ENABLE_MCP", False)),
        "sdk_available": _sdk_available(),
        "server_count": len(servers),
        "tool_count": len(list_mcp_tools(include_disabled=True)),
        "active_tool_count": len(list_mcp_tools(include_disabled=False)) if settings.ENABLE_MCP else 0,
        "servers": servers,
        "tools": list_mcp_tools(include_disabled=True),
    }


def _find_server_and_tool(tool_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    normalized = (tool_name or "").strip()
    if not normalized:
        return None, None, None

    if "__" in normalized:
        server_name, raw_tool_name = normalized.split("__", 1)
    else:
        server_name, raw_tool_name = None, normalized

    for server in list_mcp_servers():
        if server_name and server.get("name") != server_name:
            continue
        for tool_def in server.get("tools", []):
            if tool_def.get("name") == raw_tool_name:
                return server, tool_def, raw_tool_name

    return None, None, None


def get_mcp_tool_metadata(tool_name: str) -> Dict[str, Any]:
    server, tool_def, raw_tool_name = _find_server_and_tool(tool_name)
    if not server or not tool_def or not raw_tool_name:
        return {}

    return {
        "name": f"{server.get('name')}__{raw_tool_name}",
        "server": server.get("name"),
        "tool": raw_tool_name,
        "description": tool_def.get("description", ""),
        "enabled": bool(server.get("enabled", False)) and bool(tool_def.get("enabled", False)),
        "requires_approval": bool(tool_def.get("requires_approval", False)),
        "risk": tool_def.get("risk", "low"),
    }


def mcp_tool_requires_approval(tool_name: str) -> bool:
    return bool(get_mcp_tool_metadata(tool_name).get("requires_approval", False))


def _format_tool_result(result: Any) -> str:
    if getattr(result, "isError", False):
        prefix = "MCP tool returned an error:\n"
    else:
        prefix = ""

    parts = []
    for item in getattr(result, "content", []) or []:
        item_type = getattr(item, "type", "")
        if item_type == "text":
            parts.append(getattr(item, "text", ""))
        elif item_type == "image":
            mime_type = getattr(item, "mimeType", "image/*")
            parts.append(f"[MCP image content: {mime_type}]")
        elif item_type == "resource":
            resource = getattr(item, "resource", None)
            uri = getattr(resource, "uri", "unknown")
            parts.append(f"[MCP embedded resource: {uri}]")
        else:
            parts.append(str(item))

    text = "\n".join(part for part in parts if part).strip()
    return prefix + (text or str(result))


async def _call_mcp_tool_once(server: Dict[str, Any], tool_name: str, arguments: Dict[str, Any]) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=server["command"],
        args=server.get("args", []),
        env=server.get("env"),
        cwd=server.get("cwd") or str(settings.BASE_DIR),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            return _format_tool_result(result)


async def call_mcp_tool_async(tool_name: str, arguments: Dict[str, Any]) -> str:
    if not settings.ENABLE_MCP:
        return "MCP is disabled. Set ENABLE_MCP=true after configuring servers."
    if not _sdk_available():
        return "MCP SDK is not installed. Install the mcp package before live tool calls."

    server, tool_def, raw_tool_name = _find_server_and_tool(tool_name)
    if not server or not tool_def or not raw_tool_name:
        return f"MCP tool is not configured: {tool_name}"
    if not server.get("enabled", False) or not tool_def.get("enabled", False):
        return f"MCP tool is disabled: {tool_name}"

    try:
        return await asyncio.wait_for(
            _call_mcp_tool_once(server, raw_tool_name, arguments),
            timeout=settings.MCP_TOOL_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.exception("MCP tool call failed | tool=%s", tool_name)
        return f"MCP tool call failed: {exc}"


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    result: Dict[str, Any] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(call_mcp_tool_async(tool_name, arguments))
        except Exception as exc:
            result["value"] = f"MCP tool call failed: {exc}"

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_mcp_tool_async(tool_name, arguments))

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(settings.MCP_TOOL_TIMEOUT_SECONDS + 5)
    if thread.is_alive():
        return "MCP tool call timed out."
    return result.get("value", "MCP tool call returned no result.")
