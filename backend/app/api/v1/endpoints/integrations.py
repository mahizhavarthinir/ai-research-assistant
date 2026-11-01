"""
AI Research Assistant — Integration/MCP Endpoints
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DBSession, CurrentUser
from app.mcp.registry import get_tool_registry
from app.mcp.executor import execute_mcp_tool
from app.models.integration import Integration, ToolExecution

router = APIRouter()


@router.get("")
async def list_integrations(current_user: CurrentUser, db: DBSession):
    """List all available MCP tool integrations."""
    # Return DB-registered integrations
    result = await db.execute(
        select(Integration).order_by(Integration.name)
    )
    db_integrations = result.scalars().all()

    items = [
        {
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "tool_type": i.tool_type,
            "is_enabled": i.is_enabled,
            "requires_auth": i.requires_auth,
            "icon": i.icon,
        }
        for i in db_integrations
    ]

    # Also include dynamically discovered MCP tools
    try:
        registry = await get_tool_registry()
        for tool in registry.list_tools():
            items.append({
                "id": tool.qualified_name,
                "name": tool.name,
                "description": tool.description,
                "tool_type": "mcp",
                "is_enabled": tool.is_enabled,
                "requires_auth": tool.requires_auth,
                "icon": "plug",
            })
    except Exception:
        pass  # MCP registry may not be available

    return items


@router.get("/health")
async def integrations_health(current_user: CurrentUser):
    """Check the health of all configured MCP integrations."""
    try:
        registry = await get_tool_registry()
        tools = registry.list_tools()
        return {
            "status": "healthy",
            "total_tools": len(tools),
            "enabled_tools": len(registry.list_enabled_tools()),
            "integrations": [
                {"name": t.name, "server": t.server_url, "enabled": t.is_enabled}
                for t in tools
            ],
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "integrations": [],
        }


@router.post("/{integration_id}/execute")
async def execute_tool(
    integration_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Execute an MCP tool integration."""
    # Try DB-registered integration first
    result = await db.execute(
        select(Integration).where(Integration.id == integration_id)
    )
    integration = result.scalar_one_or_none()

    if integration:
        if not integration.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This integration is currently disabled",
            )
        tool_name = integration.name
    else:
        # Try MCP registry
        tool_name = integration_id

    execution_result = await execute_mcp_tool(
        tool_name=tool_name,
        arguments={},
        user_id=current_user.id,
        db=db,
    )

    if execution_result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=execution_result["error"],
        )

    return execution_result
