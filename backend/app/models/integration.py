"""
AI Research Assistant — Integration & Tool Execution Models
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)  # mcp, api, builtin
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_schema: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON schema
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<Integration '{self.name}' [{'enabled' if self.is_enabled else 'disabled'}]>"


class ToolExecution(Base, TimestampMixin):
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    integration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False  # pending, running, success, error
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<ToolExecution {self.id[:8]}... [{self.status}]>"
