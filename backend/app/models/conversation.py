"""
AI Research Assistant — Conversation & Message Models
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.sequence_number"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id[:8]}... '{self.title}'>"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False  # "user", "assistant", "system"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship("Citation", back_populates="message", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Message {self.role} #{self.sequence_number}>"
