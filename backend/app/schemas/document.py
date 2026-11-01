"""
AI Research Assistant — Document Schemas
"""

from pydantic import BaseModel, Field, HttpUrl


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int | None
    source_url: str | None
    status: str
    error_message: str | None
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class IngestURLRequest(BaseModel):
    url: str = Field(..., max_length=2000)


class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    page_number: int | None
    token_count: int

    class Config:
        from_attributes = True
