"""
AI Research Assistant — SQLAlchemy Model Base

All models inherit from this declarative base.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Import all models so Base.metadata knows about them
from app.models.user import User  # noqa: F401, E402
from app.models.conversation import Conversation, Message  # noqa: F401, E402
from app.models.document import Document, DocumentChunk  # noqa: F401, E402
from app.models.citation import Citation  # noqa: F401, E402
from app.models.integration import Integration, ToolExecution  # noqa: F401, E402
