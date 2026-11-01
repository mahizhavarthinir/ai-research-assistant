"""
AI Research Assistant — Document Endpoints
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from loguru import logger
from sqlalchemy import select, delete, or_

from app.core.config import settings
from app.core.deps import DBSession, CurrentUser
from app.models.document import Document, DocumentChunk
from app.rag.ingestor import ingest_document
from app.rag.vector_store import get_vector_store
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    IngestURLRequest,
    DocumentChunkResponse,
)

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
):
    """Upload a document (PDF, TXT, or Markdown) for indexing."""
    # Validate file extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read file content and validate size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save file to storage
    upload_dir = Path(settings.UPLOAD_DIR) / current_user.id
    upload_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    safe_filename = f"{uuid.uuid4().hex}_{filename}"
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Create database record
    document = Document(
        user_id=current_user.id,
        filename=filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        status="pending",
        storage_path=str(file_path),
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    # Trigger the ingestion pipeline
    try:
        document = await ingest_document(db, document)
    except Exception as e:
        logger.error(f"Ingestion failed for '{filename}': {e}")
        document.status = "error"
        document.error_message = str(e)[:500]
        await db.flush()

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        source_url=document.source_url,
        status=document.status,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.post("/ingest-url", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_url(data: IngestURLRequest, current_user: CurrentUser, db: DBSession):
    """Ingest a public webpage URL for indexing."""
    # Basic URL validation
    url = data.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://",
        )

    # Create database record
    document = Document(
        user_id=current_user.id,
        filename=url,
        file_type="url",
        source_url=url,
        status="pending",
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    # Trigger the ingestion pipeline
    try:
        document = await ingest_document(db, document)
    except Exception as e:
        logger.error(f"URL ingestion failed for '{url}': {e}")
        document.status = "error"
        document.error_message = str(e)[:500]
        await db.flush()

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        source_url=document.source_url,
        status=document.status,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    db: DBSession,
    query: str | None = None,
    file_type: str | None = None,
    status: str | None = None,
):
    """List all documents belonging to the current user with optional filtering."""
    stmt = select(Document).where(Document.user_id == current_user.id)

    if query and query.strip():
        term = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Document.filename.ilike(term),
                Document.source_url.ilike(term),
            )
        )

    if file_type and file_type.strip():
        ft = file_type.strip().lower()
        if ft in ("url", "web"):
            stmt = stmt.where(Document.file_type.in_(["url", "web"]))
        elif ft in ("text", "txt"):
            stmt = stmt.where(Document.file_type.in_(["txt", "md", "markdown", "csv"]))
        else:
            stmt = stmt.where(Document.file_type == ft)

    if status and status.strip():
        st = status.strip().lower()
        stmt = stmt.where(Document.status == st)

    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    documents = result.scalars().all()

    return DocumentListResponse(
        items=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                source_url=doc.source_url,
                status=doc.status,
                error_message=doc.error_message,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at.isoformat(),
            )
            for doc in documents
        ],
        total=len(documents),
    )


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document_ingestion(
    document_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Retry ingestion for a failed document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # If it's a file upload and file doesn't exist anymore, error out gracefully
    if document.file_type != "url" and document.storage_path and not os.path.exists(document.storage_path):
        document.status = "error"
        document.error_message = "Source file no longer exists on disk to retry."
        await db.flush()
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            source_url=document.source_url,
            status=document.status,
            error_message=document.error_message,
            chunk_count=document.chunk_count,
            created_at=document.created_at.isoformat(),
        )

    # 1. Clean existing chunks in DB
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )

    # 2. Clean existing vectors from ChromaDB
    try:
        store = get_vector_store()
        store.delete_by_document_id(document_id)
    except Exception as e:
        logger.warning(f"Failed to clear old vectors for document {document_id}: {e}")

    # 3. Reset document status
    document.status = "pending"
    document.error_message = None
    document.chunk_count = 0
    await db.flush()

    # 4. Re-run ingestion pipeline
    try:
        document = await ingest_document(db, document)
    except Exception as e:
        logger.error(f"Retry ingestion failed for '{document.filename}': {e}")
        document.status = "error"
        document.error_message = str(e)[:500]
        await db.flush()

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        source_url=document.source_url,
        status=document.status,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Retrieve all chunks for a specific document belonging to the user."""
    # Enforce document ownership
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    chunks = chunk_result.scalars().all()

    return [
        DocumentChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            page_number=c.page_number,
            token_count=c.token_count,
        )
        for c in chunks
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, current_user: CurrentUser, db: DBSession):
    """Get details of a specific document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        source_url=document.source_url,
        status=document.status,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, current_user: CurrentUser, db: DBSession):
    """Delete a document and its associated data."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete stored file if it exists
    if document.storage_path and os.path.exists(document.storage_path):
        os.remove(document.storage_path)

    # Remove vectors from the vector store
    try:
        store = get_vector_store()
        store.delete_by_document_id(document_id)
    except Exception as e:
        logger.warning(f"Failed to remove vectors for document {document_id}: {e}")

    await db.delete(document)
