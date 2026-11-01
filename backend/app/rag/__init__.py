"""
AI Research Assistant — RAG Pipeline Package

Handles document ingestion, chunking, embedding, and retrieval.
"""

from app.rag.chunker import chunk_text
from app.rag.embedder import get_embedding_service
from app.rag.vector_store import get_vector_store
from app.rag.retriever import get_retriever, RetrievedChunk
from app.rag.ingestor import ingest_document
from app.rag.parser import parse_file, fetch_url_content

__all__ = [
    "chunk_text",
    "get_embedding_service",
    "get_vector_store",
    "get_retriever",
    "RetrievedChunk",
    "ingest_document",
    "parse_file",
    "fetch_url_content",
]
