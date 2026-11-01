"""
AI Research Assistant — Document & DocumentChunk Models
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, txt, md, url
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # bytes
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False  # pending, processing, indexed, error
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document '{self.filename}' [{self.status}]>"


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ID in vector store

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id[:8]}... idx={self.chunk_index}>"
