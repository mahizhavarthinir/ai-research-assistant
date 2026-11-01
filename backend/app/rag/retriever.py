"""
AI Research Assistant — Retriever

Retrieves the most relevant document chunks for a user query
using embedding similarity search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.rag.embedder import get_embedding_service
from app.rag.vector_store import get_vector_store


@dataclass
class RetrievedChunk:
    """A document chunk returned from a retrieval query."""

    chunk_id: str
    content: str
    document_id: str
    document_title: str
    source_url: Optional[str]
    page_number: Optional[int]
    chunk_index: int
    relevance_score: float
    citation_index: int = 1


class Retriever:
    """Orchestrates query embedding and vector similarity search."""

    def __init__(self) -> None:
        self._embedder = get_embedding_service()
        self._store = get_vector_store()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        user_id: str | None = None,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve the most relevant document chunks for the given query.

        Args:
            query: The user's natural-language question.
            top_k: Override for the number of chunks to return.
            user_id: Optional — filter results to only this user's documents.
            document_id: Optional — filter results to a specific document.
            document_ids: Optional — filter results to multiple specific documents.

        Returns:
            A list of RetrievedChunk objects sorted by relevance (best first).
        """
        k = top_k or settings.RETRIEVAL_TOP_K

        # Multi-document retrieval: ensure balanced representation from all target documents
        if document_ids and len(document_ids) > 1:
            per_doc_k = max(3, k // len(document_ids))
            all_multi_chunks: list[RetrievedChunk] = []
            for d_id in document_ids:
                doc_chunks = self.retrieve(
                    query=query,
                    top_k=per_doc_k,
                    user_id=user_id,
                    document_id=d_id,
                )
                all_multi_chunks.extend(doc_chunks)

            # Sort combined results by relevance score descending
            all_multi_chunks.sort(key=lambda c: c.relevance_score, reverse=True)

            # Deduplicate across the combined set
            seen_chunks: list[RetrievedChunk] = []
            unique_chunks: list[RetrievedChunk] = []
            for c in all_multi_chunks:
                text_norm = " ".join(c.content.split())
                is_dup = False
                for prev in seen_chunks:
                    if c.document_id and prev.document_id and c.document_id == prev.document_id:
                        prev_text = " ".join(prev.content.split())
                        if len(text_norm) > 40 and (text_norm in prev_text or prev_text in text_norm):
                            is_dup = True
                            break
                if not is_dup:
                    seen_chunks.append(c)
                    unique_chunks.append(c)

            return unique_chunks[:k]

        if document_ids and len(document_ids) == 1:
            document_id = document_ids[0]

        # Embed the query
        query_embedding = self._embedder.embed_text(query)

        # Build optional metadata filter
        conditions = []
        if user_id:
            conditions.append({"user_id": user_id})
        if document_id:
            conditions.append({"document_id": document_id})

        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        # Search the vector store
        results = self._store.query(
            query_embedding=query_embedding,
            top_k=k,
            where=where_filter,
        )

        # Parse results into structured objects
        chunks: list[RetrievedChunk] = []

        if not results or not results.get("ids") or not results["ids"][0]:
            logger.info(f"No results found for query: '{query[:80]}...'")
            return chunks

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for i, chunk_id in enumerate(ids):
            meta = metadatas[i] if metadatas[i] else {}
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to a 0-1 relevance score (higher is better)
            relevance = max(0.0, 1.0 - (distances[i] / 2.0))

            # Skip chunks with low relevance to avoid polluting context
            if relevance < 0.45:
                continue

            # Convert ChromaDB empty-string metadata back to None
            raw_url = meta.get("source_url")
            source_url = raw_url if raw_url else None
            raw_page = meta.get("page_number")
            page_number = raw_page if raw_page and raw_page != 0 else None

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    content=documents[i],
                    document_id=meta.get("document_id", ""),
                    document_title=meta.get("document_title", "Unknown"),
                    source_url=source_url,
                    page_number=page_number,
                    chunk_index=meta.get("chunk_index", 0),
                    relevance_score=round(relevance, 4),
                )
            )

        # Deduplicate overlapping chunks from the same document section
        seen_chunks: list[RetrievedChunk] = []
        unique_chunks: list[RetrievedChunk] = []
        for c in chunks:
            text_norm = " ".join(c.content.split())
            is_dup = False
            for prev in seen_chunks:
                # Deduplication applies only within the same document
                if c.document_id and prev.document_id and c.document_id == prev.document_id:
                    prev_text = " ".join(prev.content.split())
                    if len(text_norm) > 40 and (text_norm in prev_text or prev_text in text_norm):
                        is_dup = True
                        break
            if not is_dup:
                seen_chunks.append(c)
                unique_chunks.append(c)

        logger.info(
            f"Retrieved {len(unique_chunks)} relevant chunks for query (top score: "
            f"{unique_chunks[0].relevance_score if unique_chunks else 'N/A'})"
        )
        return unique_chunks


def get_retriever() -> Retriever:
    """Convenience function to create a Retriever instance."""
    return Retriever()
