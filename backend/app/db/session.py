"""
AI Research Assistant — Database Session Management

Provides async SQLAlchemy engine and session factory.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _create_engine():
    """Create the async engine with driver-appropriate options."""
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
    else:
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )


async_engine = _create_engine()

# Session factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create database tables from models (dev convenience)."""
    from app.models import Base  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
