"""
AI Research Assistant — Research Schemas (Phase 4)

Defines data contracts for:
  - Multi-source document comparison
  - Research report generation with summaries, findings, conclusions, and citations
"""

from pydantic import BaseModel, Field
from app.schemas.chat import CitationSchema


class DocumentSummary(BaseModel):
    id: str
    filename: str
    file_type: str


class DocumentCompareRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=2, max_length=10)
    topic: str | None = Field(None, max_length=1000)
    conversation_id: str | None = None


class DocumentCompareResponse(BaseModel):
    title: str
    topic: str
    content: str
    documents: list[DocumentSummary]
    citations: list[CitationSchema] = []
    conversation_id: str | None = None
    message_id: str | None = None


class ResearchReportRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    topic: str = Field(..., min_length=3, max_length=1000)
    conversation_id: str | None = None


class ResearchReportResponse(BaseModel):
    title: str
    topic: str
    executive_summary: str
    key_findings: list[str] = []
    conclusions: str
    limitations: str
    content: str
    documents: list[DocumentSummary] = []
    citations: list[CitationSchema] = []
    conversation_id: str | None = None
    message_id: str | None = None

