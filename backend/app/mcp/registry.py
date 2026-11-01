"""
AI Research Assistant — MCP Tool Registry

Discovers and registers MCP tools from configured servers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from loguru import logger

from app.core.config import settings


@dataclass
class MCPTool:
    """Represents a single MCP tool that can be executed."""

    name: str
    description: str
    server_url: str
    input_schema: dict = field(default_factory=dict)
    requires_auth: bool = False
    is_enabled: bool = True

    @property
    def qualified_name(self) -> str:
        """Fully qualified tool name including the server."""
        return f"{self.server_url}::{self.name}"


class MCPToolRegistry:
    """Manages the discovery and registration of MCP tools."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load tool definitions from built-in research tools and configured MCP servers."""
        if self._initialized:
            return

        # ── 1. Register Built-in Research MCP Tools ──
        self._register_builtin_tools()

        if not settings.MCP_ENABLED:
            logger.info("External MCP integration is disabled; using built-in research tools.")
            self._initialized = True
            return

        try:
            servers = json.loads(settings.MCP_SERVERS)
        except json.JSONDecodeError:
            logger.error("Invalid MCP_SERVERS JSON in configuration.")
            servers = []

        for server_config in servers:
            await self._discover_server_tools(server_config)

        self._initialized = True
        logger.info(f"MCP registry initialized — {len(self._tools)} tools available.")

    def _register_builtin_tools(self) -> None:
        """Register reliable built-in research tools."""
        builtin_tools = [
            MCPTool(
                name="github_search_repositories",
                description="Search public GitHub repositories by keyword, topic, or language to find real codebases and stars.",
                server_url="builtin",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords, e.g. 'fastapi rag'"}
                    },
                    "required": ["query"],
                },
                is_enabled=True,
            ),
            MCPTool(
                name="github_search_code",
                description="Search code across GitHub repositories for specific symbols, functions, or file patterns.",
                server_url="builtin",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Code search term"}
                    },
                    "required": ["query"],
                },
                is_enabled=True,
            ),
            MCPTool(
                name="fetch_web_content",
                description="Fetch and extract live clean text content from any public web URL.",
                server_url="builtin",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Web page URL"}
                    },
                    "required": ["url"],
                },
                is_enabled=True,
            ),
            MCPTool(
                name="python_calculator",
                description="Safely evaluate mathematical expressions and calculations.",
                server_url="builtin",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression, e.g. '2 ** 10 * 3.1415'"}
                    },
                    "required": ["expression"],
                },
                is_enabled=True,
            ),
        ]

        for t in builtin_tools:
            self._tools[t.qualified_name] = t
            logger.debug(f"Registered built-in MCP tool: {t.name}")

    async def _discover_server_tools(self, server_config: dict) -> None:
        """Discover tools from a single MCP server."""
        server_url = server_config.get("url", "")
        server_name = server_config.get("name", server_url)

        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            logger.info(f"Discovering tools from MCP server: {server_name}")

            async with sse_client(url=server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools_result = await session.list_tools()
                    for tool in tools_result.tools:
                        mcp_tool = MCPTool(
                            name=tool.name,
                            description=tool.description or "",
                            server_url=server_url,
                            input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        )
                        self._tools[mcp_tool.qualified_name] = mcp_tool
                        logger.debug(f"  Registered tool: {tool.name}")

            logger.info(
                f"Discovered {len(tools_result.tools)} tools from {server_name}"
            )

        except Exception as e:
            logger.warning(f"Failed to connect to MCP server '{server_name}': {e}")

    def get_tool(self, name: str) -> MCPTool | None:
        """Look up a tool by its name or qualified name."""
        # Try exact match first
        if name in self._tools:
            return self._tools[name]
        # Try by short name
        for key, tool in self._tools.items():
            if tool.name == name:
                return tool
        return None

    def list_tools(self) -> list[MCPTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_enabled_tools(self) -> list[MCPTool]:
        """Return only enabled tools."""
        return [t for t in self._tools.values() if t.is_enabled]

    def get_tools_for_llm(self) -> list[dict]:
        """
        Format tools as function definitions for the LLM.
        This allows the LLM to decide when to invoke a tool.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
            for tool in self.list_enabled_tools()
        ]


# Module-level singleton
_registry: MCPToolRegistry | None = None


async def get_tool_registry() -> MCPToolRegistry:
    """Get the singleton MCP tool registry, initializing it if needed."""
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
        await _registry.initialize()
    return _registry
