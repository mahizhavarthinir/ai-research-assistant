"""
AI Research Assistant — Document Ingestor

Full pipeline: parse → chunk → embed → store.
Called when a document is uploaded or a URL is ingested.
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.rag.chunker import chunk_text
from app.rag.embedder import get_embedding_service
from app.rag.parser import parse_file, parse_file_sections, fetch_url_content
from app.rag.vector_store import get_vector_store


async def ingest_document(db: AsyncSession, document: Document) -> Document:
    """
    Run the full ingestion pipeline for a document.

    Steps:
        1. Parse the file/URL to extract raw text
        2. Chunk the text into overlapping segments
        3. Generate embeddings for each chunk
        4. Store embeddings in the vector store
        5. Save chunk records to the database
        6. Update the document status

    Args:
        db: Active database session.
        document: The Document model instance to ingest.

    Returns:
        The updated Document with status set to "indexed" or "error".
    """
    try:
        document.status = "processing"
        await db.flush()

        logger.info(f"Ingesting document: {document.filename} (type={document.file_type})")

        # ── Step 1: Extract text sections with page tracking ─
        if document.file_type == "url":
            raw_text = await fetch_url_content(document.source_url)
            sections = [{"page_number": None, "content": raw_text}]
        else:
            sections = await parse_file_sections(document.storage_path, document.file_type)

        if not sections or not any(s.get("content", "").strip() for s in sections):
            document.status = "error"
            document.error_message = "No text content could be extracted from this document."
            await db.flush()
            return document

        # ── Step 2: Chunk each section preserving page metadata ──
        all_chunks: list[dict] = []
        global_index = 0

        for section in sections:
            sec_text = section.get("content", "").strip()
            if not sec_text:
                continue
            sec_chunks = chunk_text(sec_text)
            page_num = section.get("page_number")
            for c in sec_chunks:
                # If page_num is not set (e.g. text file with embedded [Page X]), check content
                effective_page = page_num or _extract_page_number(c["content"])
                all_chunks.append({
                    "content": c["content"],
                    "index": global_index,
                    "page_number": effective_page,
                })
                global_index += 1

        if not all_chunks:
            document.status = "error"
            document.error_message = "Document produced no text chunks."
            await db.flush()
            return document

        logger.info(f"Created {len(all_chunks)} chunks for '{document.filename}'")

        # ── Step 3: Generate embeddings ──────────────
        embedder = get_embedding_service()
        chunk_texts = [c["content"] for c in all_chunks]
        embeddings = embedder.embed_batch(chunk_texts)

        # ── Step 4: Store in vector store ────────────
        store = get_vector_store()

        chunk_ids: list[str] = []
        db_chunks: list[DocumentChunk] = []

        for chunk_data in all_chunks:
            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["index"],
                content=chunk_data["content"],
                page_number=chunk_data["page_number"],
                token_count=len(chunk_data["content"].split()),
            )
            db.add(db_chunk)
            await db.flush()

            chunk_ids.append(db_chunk.id)
            db_chunks.append(db_chunk)

        # Prepare metadata for the vector store
        metadatas = [
            {
                "document_id": document.id,
                "document_title": document.filename,
                "source_url": document.source_url or "",
                "user_id": document.user_id,
                "chunk_index": all_chunks[i]["index"],
                "page_number": db_chunks[i].page_number or 0,
            }
            for i in range(len(all_chunks))
        ]

        store.add_documents(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        # ── Step 5: Update document status ───────────
        document.chunk_count = len(all_chunks)
        document.status = "indexed"
        document.error_message = None

        # Update vector_id references on chunks
        for i, db_chunk in enumerate(db_chunks):
            db_chunk.vector_id = chunk_ids[i]

        await db.flush()

        logger.info(
            f"Document '{document.filename}' ingested successfully — "
            f"{len(all_chunks)} chunks indexed."
        )
        return document

    except Exception as e:
        logger.error(f"Ingestion failed for '{document.filename}': {e}")
        document.status = "error"
        document.error_message = str(e)[:500]
        await db.flush()
        return document


def _extract_page_number(text: str) -> int | None:
    """Try to extract a page number from [Page N] markers in PDF text."""
    import re

    match = re.search(r"\[Page (\d+)\]", text)
    if match:
        return int(match.group(1))
    return None
