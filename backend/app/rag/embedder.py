"""
AI Research Assistant — Embedding Service

Generates vector embeddings using Sentence Transformers.
Model is lazy-loaded on first use.
"""

from __future__ import annotations

import threading
from typing import Optional

from loguru import logger

from app.core.config import settings


class EmbeddingService:
    """Wraps a Sentence Transformer model for generating text embeddings."""

    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Singleton accessor — ensures only one model is loaded."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_model(self):
        """Lazy-load the embedding model on first call."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            model_name = settings.EMBEDDING_MODEL
            logger.info(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded — dimension: {self._model.get_sentence_embedding_dimension()}")

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""
        self._load_model()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []

        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the loaded model."""
        self._load_model()
        return self._model.get_sentence_embedding_dimension()


def get_embedding_service() -> EmbeddingService:
    """Convenience function to get the singleton embedding service."""
    return EmbeddingService.get_instance()
