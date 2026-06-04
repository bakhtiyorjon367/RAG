"""Embedding service using fastembed (ONNX-based, no torch required)."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import settings
from app.services.embedding_models import register_custom_embedding_models

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings for text using fastembed."""

    def __init__(self):
        self._model: Any = None
        self._model_name = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIM

    @property
    def dimension(self) -> int:
        return self._dim

    def load_model(self) -> None:
        """Load the embedding model into memory."""
        if self._model is not None:
            return

        if settings.FASTEMBED_CACHE_PATH:
            os.environ["FASTEMBED_CACHE_PATH"] = settings.FASTEMBED_CACHE_PATH

        logger.info("Loading local embedding model: %s", self._model_name)
        register_custom_embedding_models()
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=self._model_name)
        logger.info("Embedding model loaded successfully")

    def _prefix_for_model(self, texts: list[str], prefix: str) -> list[str]:
        """Add task prefix for E5-style models; ensure single space formatting."""
        # Check if the model is from the E5 family
        if "e5" not in self._model_name.lower():
            return texts
            
        # Ensure the prefix itself ends with a space for clean concatenation
        # e.g., "passage: "
        p = prefix.strip() + " "
        return [f"{p}{t}" if t.strip() else t for t in texts]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts (e.g. document chunks).

        Embedding runs single-process (``parallel=1``) by default to keep peak
        memory predictable on low-RAM hosts. Callers should feed small batches
        (see ``settings.INGEST_BATCH_SIZE``) so memory stays flat regardless of
        document size.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        if self._model is None:
            self.load_model()

        prefixed = self._prefix_for_model(texts, "passage:")
        embeddings = list(
            self._model.embed(
                prefixed,
                batch_size=len(prefixed),
                parallel=settings.EMBED_PARALLEL,
            )
        )
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a single query string."""
        if self._model is None:
            self.load_model()
        prefixed = self._prefix_for_model([query], "query:")
        embeddings = list(self._model.embed(prefixed))
        return embeddings[0].tolist()
