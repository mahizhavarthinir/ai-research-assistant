"""
AI Research Assistant — Chat Schemas
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    document_id: str | None = None
    document_ids: list[str] | None = None


class RegenerateRequest(BaseModel):
    document_id: str | None = None
    document_ids: list[str] | None = None


class CitationSchema(BaseModel):
    id: str
    source_title: str
    source_url: str | None = None
    page_number: int | None = None
    snippet: str
    relevance_score: float | None = None
    citation_index: int

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    citations: list[CitationSchema] = []
    model_used: str | None = None


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    sequence_number: int
    citations: list[CitationSchema] = []
    created_at: str

    class Config:
        from_attributes = True


class ConversationSchema(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailSchema(ConversationSchema):
    messages: list[MessageSchema] = []


class ConversationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    pages: int
