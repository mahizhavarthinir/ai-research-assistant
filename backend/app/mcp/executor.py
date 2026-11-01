"""
AI Research Assistant — MCP Tool Executor

Executes MCP tools by connecting to the appropriate server and calling the tool.
"""

from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import MCPTool, get_tool_registry
from app.models.integration import ToolExecution


async def execute_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    user_id: str,
    conversation_id: str | None = None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Execute a registered MCP tool.

    Args:
        tool_name: Name of the tool to execute.
        arguments: Input arguments for the tool.
        user_id: ID of the requesting user.
        conversation_id: Optional conversation context.
        db: Optional database session for logging execution.

    Returns:
        A dict with "status", "result", and "error" keys.
    """
    registry = await get_tool_registry()
    tool = registry.get_tool(tool_name)

    if tool is None:
        return {
            "status": "error",
            "result": None,
            "error": f"Tool '{tool_name}' not found in the registry.",
        }

    if not tool.is_enabled:
        return {
            "status": "error",
            "result": None,
            "error": f"Tool '{tool_name}' is currently disabled.",
        }

    # Log the execution start if db session is provided and valid
    execution_record = None
    start_time = time.monotonic()

    if db:
        try:
            from sqlalchemy import select
            from app.models.integration import Integration
            # Ensure an Integration entry exists so FK constraint is satisfied
            int_res = await db.execute(select(Integration).where(Integration.name == tool.name))
            integration_obj = int_res.scalar_one_or_none()
            if not integration_obj:
                integration_obj = Integration(
                    name=tool.name,
                    description=tool.description,
                    tool_type="builtin" if tool.server_url == "builtin" else "mcp",
                    is_enabled=tool.is_enabled,
                    icon="tool",
                )
                db.add(integration_obj)
                await db.flush()

            execution_record = ToolExecution(
                integration_id=integration_obj.id,
                user_id=user_id,
                conversation_id=conversation_id,
                input_data=json.dumps(arguments),
                status="running",
            )
            db.add(execution_record)
            await db.flush()
        except Exception as log_err:
            logger.warning(f"Could not persist tool execution record: {log_err}")
            execution_record = None

    try:
        logger.info(f"Executing MCP tool: {tool_name} (server: {tool.server_url})")

        if tool.server_url == "builtin":
            result = await _execute_builtin_tool(tool.name, arguments)
        else:
            result = await _call_mcp_server(tool, arguments)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        if db and execution_record:
            try:
                execution_record.status = "success"
                execution_record.output_data = json.dumps(result, default=str)
                execution_record.duration_ms = duration_ms
                await db.flush()
            except Exception:
                pass

        logger.info(f"Tool '{tool_name}' executed successfully in {duration_ms}ms")

        return {
            "status": "success",
            "result": result,
            "error": None,
        }

    except Exception as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        error_msg = str(e)

        if db and execution_record:
            try:
                execution_record.status = "error"
                execution_record.error_message = error_msg[:500]
                execution_record.duration_ms = duration_ms
                await db.flush()
            except Exception:
                pass

        logger.error(f"Tool '{tool_name}' execution failed: {error_msg}")

        return {
            "status": "error",
            "result": None,
            "error": error_msg,
        }


async def _execute_builtin_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a built-in research tool."""
    import httpx

    if tool_name == "github_search_repositories":
        query = arguments.get("query", "").strip()
        if not query:
            return "Error: Search query is required."
        url = f"https://api.github.com/search/repositories?q={query}&per_page=5"
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "AI-Research-Assistant",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    return f"No GitHub repositories found matching '{query}'."
                lines = [f"Found {data.get('total_count', len(items))} repositories for '{query}':"]
                for repo in items[:5]:
                    lines.append(
                        f"- [{repo['full_name']}]({repo['html_url']}) ⭐ {repo['stargazers_count']} "
                        f"({repo.get('language') or 'N/A'})\n  {repo.get('description') or 'No description'}"
                    )
                return "\n".join(lines)
            else:
                return f"GitHub API returned status {resp.status_code}: {resp.text[:300]}"

    elif tool_name == "github_search_code":
        query = arguments.get("query", "").strip()
        if not query:
            return "Error: Code search query is required."
        url = f"https://api.github.com/search/code?q={query}&per_page=5"
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "AI-Research-Assistant",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    return f"No code matches found on GitHub for '{query}'."
                lines = [f"Found {data.get('total_count', len(items))} code matches for '{query}':"]
                for item in items[:5]:
                    repo = item.get("repository", {})
                    lines.append(
                        f"- {item.get('name')} in [{repo.get('full_name')}]({item.get('html_url')})\n  Path: {item.get('path')}"
                    )
                return "\n".join(lines)
            else:
                return f"GitHub API returned status {resp.status_code}: {resp.text[:300]}"

    elif tool_name == "fetch_web_content":
        url = arguments.get("url", "").strip()
        if not url:
            return "Error: URL is required."
        from app.rag.parser import fetch_url_content
        return await fetch_url_content(url)

    elif tool_name == "python_calculator":
        expr = arguments.get("expression", "").strip()
        if not expr:
            return "Error: Math expression is required."
        try:
            import math
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("_")
            }
            allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow})
            clean_expr = expr.rstrip("=")
            result = eval(clean_expr, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except Exception as e:
            return f"Calculation error: {e}"

    return f"Unknown built-in tool: {tool_name}"


async def _call_mcp_server(tool: MCPTool, arguments: dict[str, Any]) -> Any:
    """Connect to the MCP server and call the tool."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url=tool.server_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.call_tool(tool.name, arguments=arguments)

            # Extract the text content from the result
            if hasattr(result, "content") and result.content:
                # MCP results can have multiple content items
                output_parts = []
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        output_parts.append(content_item.text)
                return "\n".join(output_parts) if output_parts else str(result)

            return str(result)
