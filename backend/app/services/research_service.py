"""
AI Research Assistant — Research Service (Phase 4)

Provides:
  1. Multi-source document comparison with structured comparison matrix,
     consensus/differences analysis, and strict per-document citations.
  2. Research report generator with executive summary, key findings,
     conclusions, limitations, and reliable citations.
  3. Source-grounded synthesis that explicitly admits when information is unavailable.
"""

from __future__ import annotations

import re
from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import get_llm_provider, LLMMessage
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.rag.retriever import get_retriever, RetrievedChunk
from app.schemas.chat import CitationSchema
from app.schemas.research import (
    DocumentCompareResponse,
    DocumentSummary,
    ResearchReportResponse,
)
from app.services.chat_service import save_citations, _build_document_context


# ── System Prompts ──────────────────────────────────────────

SYSTEM_PROMPT_COMPARISON = """You are an AI Research Assistant specialized in multi-source comparative analysis.
You are comparing 2 or more research documents based on the provided source passages.

STRICT GROUNDING & CITATION RULES:
1. Base your comparative analysis strictly on the provided document passages.
2. Attribute every key statement to its source using bracketed citations: [1], [2], etc.
3. CLEARLY ADMIT UNAVAILABLE INFORMATION: If a document does not address a requested aspect or topic, explicitly state: "Document [Title] does not contain information regarding [aspect]." Never assume, extrapolate, or fabricate unstated details.
4. Distinguish between agreement/consensus and conflict/differences across the sources.

REQUIRED RESPONSE STRUCTURE:
## Comparison Overview
A concise briefing of the compared documents, their primary focus, and the scope of analysis.

## Comparative Matrix
A clear Markdown comparison table summarizing key dimensions:
| Dimension | Document 1 | Document 2 | Comparison / Notes |
(Include dimensions such as Objectives, Methodology/Approach, Key Findings, Metrics/Performance, and Limitations).

## Consensus & Shared Findings
Synthesize common ground, shared conclusions, or consistent data points supported across multiple documents, citing [X].

## Divergences & Contrasting Perspectives
Detail distinct methodologies, conflicting metrics, differing assumptions, or contradictory findings between the sources, citing [X].

## Gaps & Unavailable Information
Explicitly identify what questions remain unanswered or where specific documents lack data.

## Conclusions & Synthesis
A grounded synthesis summarizing the collective takeaway.
"""


SYSTEM_PROMPT_REPORT = """You are an AI Research Assistant specialized in synthesizing comprehensive, publication-grade research reports.
You are generating a formal Research Report based on the provided document passages.

STRICT GROUNDING & CITATION RULES:
1. All findings, metrics, and conclusions must be derived strictly from the provided passages.
2. Support all factual claims with bracketed citations: [1], [2], etc.
3. ADMIT UNAVAILABLE EVIDENCE: If the documents do not cover an aspect of the topic, explicitly state in the Limitations section: "The analyzed sources do not contain information regarding [topic]." Do not invent or guess.

REQUIRED RESPONSE STRUCTURE:
# Research Report: [Generate an Informative Title]

## Executive Summary
A high-level executive summary (2-3 paragraphs) synthesizing the core findings, context, and key conclusions.

## Analyzed Scope & Sources
List the analyzed documents, their scope, and coverage.

## Key Findings
Bulleted list of the most critical discoveries and empirical evidence, each with its citation [X].
- **[Finding 1 Title]**: Summary of finding with citation [1].
- **[Finding 2 Title]**: Summary of finding with citation [2].

## In-Depth Analysis & Thematic Synthesis
Thorough analytical discussion broken down into logical subheadings (###), examining evidence, methodologies, and technical context.

## Strategic Conclusions & Implications
Forward-looking synthesis of what the findings mean, practical takeaways, and conclusions.

## Limitations & Gaps in Evidence
Clear identification of data not present in the sources, constraints, and areas requiring further investigation.
"""


# ── Section Extraction Helpers ──────────────────────────────

def _extract_section_text(content: str, header_name: str, next_headers: list[str]) -> str:
    """Extract the content under a specific markdown heading."""
    pattern = rf"(?:^|\n)##\s+{re.escape(header_name)}[^\n]*\n([\s\S]*?)(?=(?:\n##\s+)|$)"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_bullet_points(section_text: str) -> list[str]:
    """Extract bullet points from markdown text."""
    bullets = []
    for line in section_text.splitlines():
        line_clean = line.strip()
        if line_clean.startswith(("- ", "* ", "• ")) and len(line_clean) > 3:
            bullets.append(line_clean[2:].strip())
        elif re.match(r"^\d+\.\s+", line_clean):
            bullets.append(re.sub(r"^\d+\.\s+", "", line_clean).strip())
    return bullets


# ── Comparison Service ──────────────────────────────────────

async def compare_documents(
    db: AsyncSession,
    current_user: User,
    document_ids: list[str],
    topic: str | None = None,
    conversation_id: str | None = None,
) -> DocumentCompareResponse:
    """
    Perform a multi-source comparative analysis across 2 or more user documents.
    """
    from fastapi import HTTPException, status

    # 1. Validate ownership of all document IDs
    doc_res = await db.execute(
        select(Document).where(
            Document.id.in_(document_ids),
            Document.user_id == current_user.id,
        )
    )
    docs = list(doc_res.scalars().all())
    if len(docs) != len(document_ids):
        found_ids = {d.id for d in docs}
        missing = set(document_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents not found or access denied: {list(missing)}",
        )

    doc_summaries = [
        DocumentSummary(id=d.id, filename=d.filename, file_type=d.file_type)
        for d in docs
    ]
    doc_titles_str = ", ".join(f"'{d.filename}'" for d in docs)
    effective_topic = (topic or "").strip() or f"Comparative analysis of {doc_titles_str}"

    # 2. Retrieve balanced evidence from all selected documents
    retriever = get_retriever()
    chunks = retriever.retrieve(
        query=effective_topic,
        top_k=max(8, len(document_ids) * 4),
        user_id=current_user.id,
        document_ids=document_ids,
    )

    # 3. Build multi-source context
    if chunks:
        context_str = _build_document_context(chunks)
    else:
        context_str = (
            f"NOTICE: No high-relevance passages were retrieved across the specified documents "
            f"({doc_titles_str}) for the topic '{effective_topic}'. "
            f"Explicitly inform the user that the selected documents do not provide information on this topic."
        )

    # 4. Construct prompt and invoke LLM
    llm = get_llm_provider()
    user_prompt = (
        f"{context_str}\n\n---\n\n"
        f"DOCUMENTS TO COMPARE: {doc_titles_str}\n"
        f"RESEARCH TOPIC / FOCUS: {effective_topic}\n\n"
        f"Please provide a rigorous comparative analysis strictly grounded in the context above."
    )

    response = await llm.generate(
        messages=[LLMMessage(role="user", content=user_prompt)],
        system_prompt=SYSTEM_PROMPT_COMPARISON,
        temperature=0.2,
    )
    content = response.content

    # 5. Strict citation filtering
    cited_nums = set(int(m) for m in re.findall(r'\[(\d+)\]', content))
    if cited_nums and chunks:
        cited_chunks = [c for c in chunks if getattr(c, "citation_index", None) in cited_nums]
        if cited_chunks:
            chunks = cited_chunks
    elif not cited_nums:
        chunks = []

    # 6. Optionally save to conversation
    message_id = None
    if conversation_id:
        conv_res = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = conv_res.scalar_one_or_none()
        if conversation:
            # Get seq number
            count_res = await db.execute(
                select(func.count()).where(Message.conversation_id == conversation.id)
            )
            seq = count_res.scalar() or 0

            # Save user prompt
            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=f"📊 **Compare Documents:** {doc_titles_str}\n**Focus:** {effective_topic}",
                sequence_number=seq,
            )
            db.add(user_msg)
            await db.flush()

            # Save assistant comparison
            assist_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=content,
                sequence_number=seq + 1,
            )
            db.add(assist_msg)
            await db.flush()
            message_id = assist_msg.id

            if chunks:
                await save_citations(db, assist_msg.id, chunks)

    # Convert chunks to CitationSchema
    citations = [
        CitationSchema(
            id=c.chunk_id,
            source_title=c.document_title,
            source_url=c.source_url,
            page_number=c.page_number,
            snippet=c.content[:300],
            relevance_score=c.relevance_score,
            citation_index=c.citation_index,
        )
        for c in chunks
    ]

    title = f"Document Comparison: {docs[0].filename} vs {docs[1].filename}" + (f" (+{len(docs)-2} more)" if len(docs) > 2 else "")

    return DocumentCompareResponse(
        title=title,
        topic=effective_topic,
        content=content,
        documents=doc_summaries,
        citations=citations,
        conversation_id=conversation_id,
        message_id=message_id,
    )


# ── Report Generation Service ───────────────────────────────

async def generate_research_report(
    db: AsyncSession,
    current_user: User,
    document_ids: list[str] | None = None,
    topic: str = "",
    conversation_id: str | None = None,
) -> ResearchReportResponse:
    """
    Generate a structured, publication-grade research report on a topic.
    """
    from fastapi import HTTPException, status

    topic_clean = topic.strip()
    if not topic_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Research report topic cannot be empty",
        )

    # 1. Resolve documents
    if document_ids and len(document_ids) > 0:
        docs_res = await db.execute(
            select(Document).where(
                Document.id.in_(document_ids),
                Document.user_id == current_user.id,
            )
        )
        docs = list(docs_res.scalars().all())
        if len(docs) != len(document_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more specified documents not found or access denied",
            )
    else:
        # Use all indexed documents belonging to this user
        docs_res = await db.execute(
            select(Document).where(
                Document.user_id == current_user.id,
                Document.status == "indexed",
            )
        )
        docs = list(docs_res.scalars().all())

    doc_summaries = [
        DocumentSummary(id=d.id, filename=d.filename, file_type=d.file_type)
        for d in docs
    ]
    doc_titles_str = ", ".join(f"'{d.filename}'" for d in docs) if docs else "None"

    # 2. Retrieve multi-aspect chunks
    retriever = get_retriever()
    resolved_ids = [d.id for d in docs] if docs else None
    chunks = retriever.retrieve(
        query=topic_clean,
        top_k=14,
        user_id=current_user.id,
        document_ids=resolved_ids,
    )

    # 3. Context & Guard
    if chunks:
        context_str = _build_document_context(chunks)
    else:
        context_str = (
            f"NOTICE: No relevant context passages were found in the user's documents for the topic '{topic_clean}'. "
            f"You must explicitly state that the documents do not provide information on this topic in the Executive Summary and Limitations."
        )

    # 4. LLM Generation
    llm = get_llm_provider()
    user_prompt = (
        f"{context_str}\n\n---\n\n"
        f"RESEARCH TOPIC: {topic_clean}\n"
        f"AVAILABLE SOURCES: {doc_titles_str}\n\n"
        f"Please compose a comprehensive, well-structured research report following the required structure."
    )

    response = await llm.generate(
        messages=[LLMMessage(role="user", content=user_prompt)],
        system_prompt=SYSTEM_PROMPT_REPORT,
        temperature=0.2,
    )
    content = response.content

    # 5. Extract structured report components
    exec_summary = _extract_section_text(content, "Executive Summary", ["Analyzed Scope", "Key Findings"])
    if not exec_summary:
        exec_summary = content[:400].strip()

    findings_text = _extract_section_text(content, "Key Findings", ["In-Depth Analysis", "Detailed Analysis"])
    key_findings = _extract_bullet_points(findings_text)
    if not key_findings:
        key_findings = [line.strip() for line in findings_text.splitlines() if line.strip()][:5]

    conclusions = _extract_section_text(content, "Strategic Conclusions & Implications", ["Limitations", "References"])
    if not conclusions:
        conclusions = _extract_section_text(content, "Conclusions", ["Limitations", "References"])

    limitations = _extract_section_text(content, "Limitations & Gaps in Evidence", ["References"])
    if not limitations:
        limitations = _extract_section_text(content, "Limitations", ["References"])

    # Extract title from H1 if present
    h1_match = re.search(r"^#\s+Research Report:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    if h1_match:
        report_title = h1_match.group(1).strip()
    else:
        first_h1 = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        report_title = first_h1.group(1).strip() if first_h1 else f"Research Report: {topic_clean}"

    # 6. Strict citation filtering
    cited_nums = set(int(m) for m in re.findall(r'\[(\d+)\]', content))
    if cited_nums and chunks:
        cited_chunks = [c for c in chunks if getattr(c, "citation_index", None) in cited_nums]
        if cited_chunks:
            chunks = cited_chunks
    elif not cited_nums:
        chunks = []

    # 7. Optionally save to conversation
    message_id = None
    if conversation_id:
        conv_res = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = conv_res.scalar_one_or_none()
        if conversation:
            count_res = await db.execute(
                select(func.count()).where(Message.conversation_id == conversation.id)
            )
            seq = count_res.scalar() or 0

            user_msg = Message(
                conversation_id=conversation.id,
                role="user",
                content=f"📑 **Generate Research Report:** {topic_clean}",
                sequence_number=seq,
            )
            db.add(user_msg)
            await db.flush()

            assist_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=content,
                sequence_number=seq + 1,
            )
            db.add(assist_msg)
            await db.flush()
            message_id = assist_msg.id

            if chunks:
                await save_citations(db, assist_msg.id, chunks)

    citations = [
        CitationSchema(
            id=c.chunk_id,
            source_title=c.document_title,
            source_url=c.source_url,
            page_number=c.page_number,
            snippet=c.content[:300],
            relevance_score=c.relevance_score,
            citation_index=c.citation_index,
        )
        for c in chunks
    ]

    return ResearchReportResponse(
        title=report_title,
        topic=topic_clean,
        executive_summary=exec_summary,
        key_findings=key_findings,
        conclusions=conclusions,
        limitations=limitations,
        content=content,
        documents=doc_summaries,
        citations=citations,
        conversation_id=conversation_id,
        message_id=message_id,
    )

