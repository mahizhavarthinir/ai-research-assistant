"""
AI Research Assistant — Citation Model
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Citation(Base, TimestampMixin):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    message = relationship("Message", back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation [{self.citation_index}] '{self.source_title[:30]}...'>"
