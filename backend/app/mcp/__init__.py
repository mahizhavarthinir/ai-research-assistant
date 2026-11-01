"""
AI Research Assistant — MCP Integration Package

Model Context Protocol tool registry and execution.
"""

from app.mcp.registry import MCPTool, MCPToolRegistry, get_tool_registry
from app.mcp.executor import execute_mcp_tool

__all__ = [
    "MCPTool",
    "MCPToolRegistry",
    "get_tool_registry",
    "execute_mcp_tool",
]
