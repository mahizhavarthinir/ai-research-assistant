"""
AI Research Assistant — Research Endpoints (Phase 4)

Endpoints:
  - POST /api/v1/research/compare : Multi-source document comparison
  - POST /api/v1/research/report  : Research report generator with executive summary,
                                    key findings, conclusions, and citations
  - POST /api/v1/research/export  : Export research reports/comparisons as MD or JSON
"""

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from loguru import logger

from app.core.deps import DBSession, CurrentUser
from app.schemas.research import (
    DocumentCompareRequest,
    DocumentCompareResponse,
    ResearchReportRequest,
    ResearchReportResponse,
)
from app.services.research_service import (
    compare_documents,
    generate_research_report,
)
from app.services.export_service import (
    export_research_to_pdf,
    export_research_to_docx,
)

router = APIRouter()


@router.post("/compare", response_model=DocumentCompareResponse)
async def compare_documents_endpoint(
    data: DocumentCompareRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Compare 2 or more documents with a structured comparison matrix,
    consensus analysis, divergences, and reliable citations.
    """
    if len(data.document_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 document IDs are required for comparison",
        )

    return await compare_documents(
        db=db,
        current_user=current_user,
        document_ids=data.document_ids,
        topic=data.topic,
        conversation_id=data.conversation_id,
    )


@router.post("/report", response_model=ResearchReportResponse)
async def generate_report_endpoint(
    data: ResearchReportRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Generate a publication-grade research report on a topic across specified
    documents (or all indexed user documents) with executive summary,
    key findings, conclusions, limitations, and citations.
    """
    return await generate_research_report(
        db=db,
        current_user=current_user,
        document_ids=data.document_ids,
        topic=data.topic,
        conversation_id=data.conversation_id,
    )


@router.post("/export")
async def export_research_content(
    payload: dict,
    current_user: CurrentUser,
    format: str = Query("markdown"),
):
    """
    Export a generated research report or comparison as PDF (.pdf), Word (.docx),
    Markdown (.md), or JSON (.json).
    """
    fmt = format.lower().strip()
    if fmt not in ("markdown", "md", "json", "pdf", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export format must be 'pdf', 'docx', 'markdown', or 'json'",
        )

    title = payload.get("title", "Research_Document")
    clean_title = re.sub(r"[^\w\s-]", "", title).strip()
    clean_title = re.sub(r"[-\s]+", "_", clean_title)[:50] or "Research_Document"

    content = payload.get("content", "")
    citations = payload.get("citations", [])

    # 1. PDF Export
    if fmt == "pdf":
        try:
            pdf_bytes = export_research_to_pdf(payload)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.pdf"',
                    "Content-Length": str(len(pdf_bytes)),
                },
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF for research report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF export: {str(e)}",
            )

    # 2. DOCX Export
    if fmt == "docx":
        try:
            docx_bytes = export_research_to_docx(payload)
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.docx"',
                    "Content-Length": str(len(docx_bytes)),
                },
            )
        except Exception as e:
            logger.error(f"Failed to generate Word document for research report: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Word document export: {str(e)}",
            )

    # 3. Markdown Export
    if fmt in ("markdown", "md"):
        lines = [
            f"# {title}",
            f"*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | AI Research Assistant*",
            "",
            "---",
            "",
            content,
            "",
        ]
        if citations:
            lines.append("## Verified Source Citations")
            for c in citations:
                page_str = f" (Page {c.get('page_number')})" if c.get("page_number") else ""
                url_str = f" - [{c.get('source_url')}]({c.get('source_url')})" if c.get("source_url") else ""
                lines.append(f"- **[{c.get('citation_index', 1)}]** {c.get('source_title', 'Source')}{page_str}{url_str}")
                if c.get("snippet"):
                    lines.append(f"  > \"{c.get('snippet')}\"")

        return Response(
            content="\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.md"'},
        )

    # 4. JSON Export
    export_data = {
        "title": title,
        "topic": payload.get("topic", ""),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": payload.get("executive_summary", ""),
        "key_findings": payload.get("key_findings", []),
        "conclusions": payload.get("conclusions", ""),
        "limitations": payload.get("limitations", ""),
        "content": content,
        "documents": payload.get("documents", []),
        "citations": citations,
    }
    return Response(
        content=json.dumps(export_data, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{clean_title}.json"'},
    )

