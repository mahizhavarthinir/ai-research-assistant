"""
AI Research Assistant — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.db.session import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Starting AI Research Assistant API...")

    # Initialize database tables (dev convenience — use Alembic in production)
    await init_db()
    logger.info("Database initialized.")

    # Initialize MCP tool registry and seed database integrations
    try:
        from app.mcp.registry import get_tool_registry
        from app.db.session import async_session_factory
        from app.models.integration import Integration
        from sqlalchemy import select

        registry = await get_tool_registry()
        logger.info(f"MCP registry ready — {len(registry.list_tools())} tools discovered.")

        async with async_session_factory() as session:
            for tool in registry.list_tools():
                res = await session.execute(select(Integration).where(Integration.name == tool.name))
                if not res.scalar_one_or_none():
                    session.add(
                        Integration(
                            name=tool.name,
                            description=tool.description,
                            tool_type="builtin" if tool.server_url == "builtin" else "mcp",
                            is_enabled=tool.is_enabled,
                            icon="tool",
                        )
                    )
            await session.commit()
    except Exception as e:
        logger.warning(f"MCP initialization skipped: {e}")

    yield

    logger.info("Shutting down AI Research Assistant API...")


def create_application() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="AI Research Assistant API — RAG + LLM + MCP",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=r"^https://.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_application()


# ── Health Endpoints ─────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/ready", tags=["System"])
async def readiness_check():
    """Readiness check — verifies database connectivity."""
    try:
        from app.db.session import async_engine
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "database": "disconnected"}
