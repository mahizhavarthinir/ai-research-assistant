"""
AI Research Assistant — Chat Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from loguru import logger
from sqlalchemy import select, func, delete

from app.core.deps import DBSession, CurrentUser
from app.llm.factory import reset_provider
from app.models.conversation import Conversation, Message
from app.models.citation import Citation
from app.models.document import Document
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationSchema,
    ConversationDetailSchema,
    ConversationSchema,
    ConversationUpdateRequest,
    MessageSchema,
    RegenerateRequest,
)
from app.services.chat_service import generate_chat_response, save_citations
from app.services.export_service import export_conversation_to_pdf, export_conversation_to_docx

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def send_message(data: ChatRequest, current_user: CurrentUser, db: DBSession):
    """
    Send a message and receive an AI-generated response.
    Creates a new conversation if conversation_id is not provided.
    """
    # Create or retrieve conversation
    if data.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == data.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Auto-generate a title from the first message
        title = data.message[:80] + ("..." if len(data.message) > 80 else "")
        conversation = Conversation(title=title, user_id=current_user.id)
        db.add(conversation)
        await db.flush()

    # Get next sequence number
    count_result = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation.id)
    )
    seq = count_result.scalar() or 0

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
        sequence_number=seq,
    )
    db.add(user_message)
    await db.flush()

    # Validate document ownership if document-scoped chat is requested
    scoped_doc_id = data.document_id.strip() if data.document_id and data.document_id.strip() else None
    scoped_doc_ids = [d.strip() for d in data.document_ids if d and d.strip()] if data.document_ids else None

    if scoped_doc_id:
        doc_res = await db.execute(
            select(Document).where(
                Document.id == scoped_doc_id,
                Document.user_id == current_user.id,
            )
        )
        if not doc_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{scoped_doc_id}' not found or access denied",
            )

    if scoped_doc_ids:
        docs_res = await db.execute(
            select(Document).where(
                Document.id.in_(scoped_doc_ids),
                Document.user_id == current_user.id,
            )
        )
        found_docs = list(docs_res.scalars().all())
        if len(found_docs) != len(scoped_doc_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more specified documents not found or access denied",
            )

    # Generate AI response using RAG + LLM pipeline
    try:
        assistant_content, retrieved_chunks, model_name = await generate_chat_response(
            db=db,
            conversation=conversation,
            user_message=data.message,
            user_id=current_user.id,
            document_id=scoped_doc_id,
            document_ids=scoped_doc_ids,
        )
    except Exception as e:
        # Surface the actual error instead of silently falling back to
        # the BuiltinProvider (which is a hardcoded dictionary, not an LLM).
        from loguru import logger
        from app.llm.factory import reset_provider
        logger.error(f"LLM generation failed: {e}")

        # Reset the cached provider so the next request re-initializes
        # (picks up corrected config / recovers from transient errors).
        reset_provider()

        error_detail = str(e)
        assistant_content = (
            f"⚠️ **AI service error** — I could not generate a response.\n\n"
            f"**Error:** `{error_detail}`\n\n"
            f"This usually means the LLM provider (Gemini/OpenAI/Ollama) is "
            f"misconfigured or temporarily unavailable. Please check your "
            f"backend `.env` settings and try again."
        )
        retrieved_chunks = []
        model_name = "error"

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        sequence_number=seq + 1,
    )
    db.add(assistant_message)
    await db.flush()

    # Save citations from retrieved chunks
    citations = []
    if retrieved_chunks:
        citation_records = await save_citations(db, assistant_message.id, retrieved_chunks)
        citations = [
            CitationSchema(
                id=c.id,
                source_title=c.source_title,
                source_url=c.source_url,
                page_number=c.page_number,
                snippet=c.snippet,
                relevance_score=c.relevance_score,
                citation_index=c.citation_index,
            )
            for c in citation_records
        ]

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        content=assistant_content,
        citations=citations,
        model_used=model_name,
    )


@router.get("/conversations", response_model=list[ConversationSchema])
async def list_conversations(
    current_user: CurrentUser,
    db: DBSession,
    query: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all conversations for the current user, optionally filtered by title."""
    offset = (page - 1) * per_page
    stmt = select(Conversation).where(Conversation.user_id == current_user.id)
    if query and query.strip():
        stmt = stmt.where(Conversation.title.ilike(f"%{query.strip()}%"))
    stmt = stmt.order_by(Conversation.updated_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        msg_count = await db.execute(
            select(func.count()).where(Message.conversation_id == conv.id)
        )
        items.append(
            ConversationSchema(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=msg_count.scalar() or 0,
            )
        )

    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailSchema)
async def get_conversation(conversation_id: str, current_user: CurrentUser, db: DBSession):
    """Get a conversation with all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number)
    )
    messages = messages_result.scalars().all()

    # Load citations for each assistant message
    message_schemas = []
    for msg in messages:
        msg_citations = []
        if msg.role == "assistant":
            cit_result = await db.execute(
                select(Citation)
                .where(Citation.message_id == msg.id)
                .order_by(Citation.citation_index)
            )
            msg_citations = [
                CitationSchema(
                    id=c.id,
                    source_title=c.source_title,
                    source_url=c.source_url,
                    page_number=c.page_number,
                    snippet=c.snippet,
                    relevance_score=c.relevance_score,
                    citation_index=c.citation_index,
                )
                for c in cit_result.scalars().all()
            ]

        message_schemas.append(
            MessageSchema(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sequence_number=msg.sequence_number,
                citations=msg_citations,
                created_at=msg.created_at.isoformat(),
            )
        )

    return ConversationDetailSchema(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=len(messages),
        messages=message_schemas,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationSchema)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdateRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Rename a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.title = data.title
    await db.flush()

    msg_count = await db.execute(
        select(func.count()).where(Message.conversation_id == conversation.id)
    )

    return ConversationSchema(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=msg_count.scalar() or 0,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, current_user: CurrentUser, db: DBSession):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)


@router.post("/conversations/{conversation_id}/regenerate", response_model=ChatResponse)
async def regenerate_latest_response(
    conversation_id: str,
    current_user: CurrentUser,
    db: DBSession,
    data: RegenerateRequest | None = None,
):
    """
    Regenerate the latest assistant response in the conversation.
    Replaces the previous assistant message and its citations,
    preserving all previous message sequence ordering.
    """
    # 1. Enforce conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 2. Get messages ordered by sequence
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number.asc())
    )
    messages = list(messages_result.scalars().all())
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot regenerate an empty conversation",
        )

    # 3. Identify target turn
    last_msg = messages[-1]
    if last_msg.role == "assistant":
        user_msgs = [m for m in messages[:-1] if m.role == "user"]
        if not user_msgs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No preceding user message to regenerate",
            )
        target_user_msg = user_msgs[-1]

        # Delete citations for this assistant message
        await db.execute(delete(Citation).where(Citation.message_id == last_msg.id))
        # Delete old assistant message
        await db.delete(last_msg)
        await db.flush()
    elif last_msg.role == "user":
        target_user_msg = last_msg
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot regenerate from this message state",
        )

    # 4. Validate document ownership if scoped
    scoped_doc_id = (
        data.document_id.strip()
        if data and data.document_id and data.document_id.strip()
        else None
    )
    scoped_doc_ids = (
        [d.strip() for d in data.document_ids if d and d.strip()]
        if data and data.document_ids
        else None
    )

    if scoped_doc_id:
        doc_res = await db.execute(
            select(Document).where(
                Document.id == scoped_doc_id,
                Document.user_id == current_user.id,
            )
        )
        if not doc_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{scoped_doc_id}' not found or access denied",
            )

    if scoped_doc_ids:
        docs_res = await db.execute(
            select(Document).where(
                Document.id.in_(scoped_doc_ids),
                Document.user_id == current_user.id,
            )
        )
        found_docs = list(docs_res.scalars().all())
        if len(found_docs) != len(scoped_doc_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more specified documents not found or access denied",
            )

    # 5. Generate AI response
    try:
        assistant_content, retrieved_chunks, model_name = await generate_chat_response(
            db=db,
            conversation=conversation,
            user_message=target_user_msg.content,
            user_id=current_user.id,
            document_id=scoped_doc_id,
            document_ids=scoped_doc_ids,
        )
    except Exception as e:
        logger.error(f"Regeneration failed: {e}")
        reset_provider()
        error_detail = str(e)
        assistant_content = (
            f"⚠️ **AI service error** — I could not regenerate a response.\n\n"
            f"**Error:** `{error_detail}`\n\n"
            f"Please check your backend `.env` settings and try again."
        )
        retrieved_chunks = []
        model_name = "error"

    # 6. Save new assistant message
    new_assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
        sequence_number=target_user_msg.sequence_number + 1,
    )
    db.add(new_assistant_message)
    await db.flush()

    # 7. Save citations
    citations = []
    if retrieved_chunks:
        citation_records = await save_citations(db, new_assistant_message.id, retrieved_chunks)
        citations = [
            CitationSchema(
                id=c.id,
                source_title=c.source_title,
                source_url=c.source_url,
                page_number=c.page_number,
                snippet=c.snippet,
                relevance_score=c.relevance_score,
                citation_index=c.citation_index,
            )
            for c in citation_records
        ]

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=new_assistant_message.id,
        content=assistant_content,
        citations=citations,
        model_used=model_name,
    )


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    current_user: CurrentUser,
    db: DBSession,
    format: str = Query("json"),
):
    """
    Export a conversation as PDF, Word (.docx), Markdown, or JSON including all messages and citations.
    """
    fmt = format.lower().strip()
    if fmt not in ("json", "markdown", "md", "pdf", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export format must be 'pdf', 'docx', 'markdown', or 'json'",
        )

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sequence_number.asc())
    )
    messages = list(messages_result.scalars().all())

    import json
    import re
    from datetime import datetime, timezone

    # Sanitize title for filename
    clean_title = (
        re.sub(r"[^a-zA-Z0-9_\- ]", "", conversation.title).strip().replace(" ", "_")[:40]
        or "conversation"
    )

    # Prepare structured message records with citations
    message_items: list[dict] = []
    for msg in messages:
        citations_data = []
        if msg.role == "assistant":
            cit_res = await db.execute(
                select(Citation)
                .where(Citation.message_id == msg.id)
                .order_by(Citation.citation_index.asc())
            )
            citations = cit_res.scalars().all()
            citations_data = [
                {
                    "citation_index": c.citation_index,
                    "source_title": c.source_title,
                    "source_url": c.source_url,
                    "page_number": c.page_number,
                    "snippet": c.snippet,
                    "relevance_score": c.relevance_score,
                }
                for c in citations
            ]

        message_items.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content or "",
            "sequence_number": msg.sequence_number,
            "created_at": msg.created_at.isoformat() if hasattr(msg.created_at, "isoformat") else str(msg.created_at),
            "citations": citations_data,
        })

    # 1. PDF Export
    if fmt == "pdf":
        try:
            pdf_bytes = export_conversation_to_pdf(
                conversation_title=conversation.title,
                messages=message_items,
            )
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.pdf"',
                    "Content-Length": str(len(pdf_bytes)),
                },
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF for conversation {conversation_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF export: {str(e)}",
            )

    # 2. DOCX Export
    if fmt == "docx":
        try:
            docx_bytes = export_conversation_to_docx(
                conversation_title=conversation.title,
                messages=message_items,
            )
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.docx"',
                    "Content-Length": str(len(docx_bytes)),
                },
            )
        except Exception as e:
            logger.error(f"Failed to generate Word document for conversation {conversation_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Word document export: {str(e)}",
            )

    # 3. Markdown Export
    if fmt in ("markdown", "md"):
        lines = [
            f"# {conversation.title}",
            f"*Exported on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | AI Research Assistant*",
            "",
            "---",
            "",
        ]
        for item in message_items:
            speaker = "User" if item["role"] == "user" else "Assistant"
            lines.append(f"### {speaker}")
            lines.append("")
            lines.append(item["content"].strip())
            lines.append("")

            if item["citations"]:
                lines.append("**Verified Sources Cited:**")
                for c in item["citations"]:
                    page_str = f" (Page {c['page_number']})" if c.get("page_number") else ""
                    url_str = f" - [{c['source_url']}]({c['source_url']})" if c.get("source_url") else ""
                    lines.append(f"- **[{c['citation_index']}]** {c['source_title']}{page_str}{url_str}")
                    snippet_clean = (c.get("snippet") or "").replace("\n", " ").strip()
                    if snippet_clean:
                        lines.append(f"  > {snippet_clean}")
                lines.append("")
            lines.append("---")
            lines.append("")

        md_content = "\n".join(lines)
        return Response(
            content=md_content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{clean_title}.md"'},
        )

    # 4. JSON Export
    payload = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if hasattr(conversation.created_at, "isoformat") else str(conversation.created_at),
        "updated_at": conversation.updated_at.isoformat() if hasattr(conversation.updated_at, "isoformat") else str(conversation.updated_at),
        "message_count": len(message_items),
        "messages": message_items,
    }
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{clean_title}.json"'},
    )
