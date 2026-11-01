"""
AI Research Assistant — Vector Store Client

Manages ChromaDB collections for storing and querying document embeddings.
"""

from __future__ import annotations

import threading
from typing import Optional

import chromadb
from loguru import logger

from app.core.config import settings


class VectorStore:
    """ChromaDB vector store for document chunk embeddings."""

    _instance: Optional["VectorStore"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None

    @classmethod
    def get_instance(cls) -> "VectorStore":
        """Singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _connect(self):
        """Lazy-connect to the ChromaDB server or persistent local client instantly."""
        if self._client is None:
            import socket

            # Probe port with a fast timeout (200ms) to avoid hanging
            is_server_up = False
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.2)
                    is_server_up = (sock.connect_ex((settings.CHROMA_HOST, settings.CHROMA_PORT)) == 0)
            except Exception:
                is_server_up = False

            if is_server_up:
                try:
                    logger.info(f"Connecting to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
                    self._client = chromadb.HttpClient(
                        host=settings.CHROMA_HOST,
                        port=settings.CHROMA_PORT,
                    )
                    self._client.heartbeat()
                    logger.info("ChromaDB HTTP connection established.")
                except Exception as e:
                    logger.warning(f"ChromaDB HTTP connect failed: {e}")
                    self._client = None

            if self._client is None:
                logger.info("Using local ChromaDB persistent client at ./chroma_data")
                self._client = chromadb.PersistentClient(path="./chroma_data")

    def _get_collection(self):
        """Get or create the document collection."""
        if self._collection is None:
            self._connect()
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB collection '{settings.CHROMA_COLLECTION}' ready — "
                f"{self._collection.count()} vectors stored."
            )
        return self._collection

    def add_documents(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        """
        Add document chunks with their embeddings to the vector store.

        Args:
            ids: Unique identifiers for each chunk (e.g. chunk UUIDs).
            embeddings: Pre-computed embedding vectors.
            documents: Raw text content of each chunk.
            metadatas: Optional metadata dicts for filtering.
        """
        collection = self._get_collection()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{}] * len(ids),
        )
        logger.debug(f"Added {len(ids)} vectors to the store.")

    def query(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        where: dict | None = None,
    ) -> dict:
        """
        Query the vector store for similar documents.

        Args:
            query_embedding: The embedding vector of the user's query.
            top_k: Number of results to return.
            where: Optional metadata filter dict.

        Returns:
            ChromaDB query result dict with keys: ids, distances, documents, metadatas.
        """
        collection = self._get_collection()
        k = top_k or settings.RETRIEVAL_TOP_K

        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        results = collection.query(**query_params)
        return results

    def delete_by_document_id(self, document_id: str) -> None:
        """Remove all vectors associated with a specific document."""
        collection = self._get_collection()
        collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted vectors for document {document_id}")

    def count(self) -> int:
        """Return the total number of vectors in the collection."""
        collection = self._get_collection()
        return collection.count()

    def reset_collection(self) -> None:
        """Delete and recreate the collection (use with caution)."""
        self._connect()
        self._client.delete_collection(settings.CHROMA_COLLECTION)
        self._collection = None
        logger.warning(f"Collection '{settings.CHROMA_COLLECTION}' has been reset.")


def get_vector_store() -> VectorStore:
    """Convenience function to get the singleton vector store."""
    return VectorStore.get_instance()
