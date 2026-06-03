"""Ingestion orchestrator: extract → chunk → embed → store."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.core.supabase_client import get_supabase_client
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.services.extraction import ExtractionService
from app.services.korean_normalizer import normalize_for_fts

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates the full document ingestion pipeline."""

    def __init__(self, embedding_service: EmbeddingService):
        self._extraction = ExtractionService()
        self._chunking = ChunkingService()
        self._embedding = embedding_service
        self._supabase = get_supabase_client()

    def compute_content_hash(self, file_bytes: bytes) -> str:
        """Compute SHA-256 hash of file bytes for deduplication."""
        return hashlib.sha256(file_bytes).hexdigest()

    def check_duplicate(self, user_id: str, content_hash: str) -> dict[str, Any] | None:
        """Check if a document with the same content hash exists for this user.

        Returns the existing document record if found, None otherwise.
        """
        result = (
            self._supabase.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("content_hash", content_hash)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    def upload_to_storage(
        self, user_id: str, filename: str, file_bytes: bytes, mime_type: str
    ) -> str:
        """Upload the raw file to Supabase Storage.

        Returns the storage path.
        """
        import os
        import uuid

        _, ext = os.path.splitext(filename)
        storage_path = f"{user_id}/{uuid.uuid4()}{ext}"
        self._supabase.storage.from_("documents").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type},
        )
        return storage_path

    def create_document_record(
        self,
        user_id: str,
        filename: str,
        storage_path: str,
        mime_type: str,
        content_hash: str,
    ) -> dict[str, Any]:
        """Create a document row with status=processing."""
        result = (
            self._supabase.table("documents")
            .insert(
                {
                    "user_id": user_id,
                    "filename": filename,
                    "storage_path": storage_path,
                    "mime_type": mime_type,
                    "content_hash": content_hash,
                    "status": "processing",
                    "metadata": {},
                }
            )
            .execute()
        )
        return result.data[0]

    def process_document(
        self,
        document_id: str,
        file_bytes: bytes,
        mime_type: str,
        filename: str,
    ) -> None:
        """Run the full ingestion pipeline for a document.

        Steps: extract text → chunk → embed → store chunks → update status.
        """
        try:
            # Step 1: Extract text
            logger.info("Extracting text from document %s", document_id)
            extraction_result = self._extraction.extract(file_bytes, mime_type, filename)

            # Update document metadata with extraction results
            self._supabase.table("documents").update(
                {"metadata": extraction_result.metadata}
            ).eq("id", document_id).execute()

            # Step 2: Chunk
            logger.info("Chunking document %s", document_id)
            chunks = self._chunking.split(
                extraction_result.text,
                doc_metadata=extraction_result.metadata,
            )

            if not chunks:
                logger.warning("No chunks generated for document %s", document_id)
                self._supabase.table("documents").update(
                    {
                        "status": "ready",
                        "metadata": {
                            **extraction_result.metadata,
                            "chunk_count": 0,
                        },
                    }
                ).eq("id", document_id).execute()
                return

            # Step 3: Embed
            logger.info("Embedding %d chunks for document %s", len(chunks), document_id)
            texts = [chunk.content for chunk in chunks]
            embeddings = self._embedding.embed_texts(texts)

            # Step 4: Store chunks
            logger.info("Storing %d chunks for document %s", len(chunks), document_id)
            chunk_records = []
            for chunk, embedding in zip(chunks, embeddings):
                normalized = normalize_for_fts(chunk.content)
                chunk_records.append({
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "content_normalized": normalized if (normalized and normalized.strip()) else None,
                    "embedding": embedding,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                })

            # Bulk insert chunks
            self._supabase.table("chunks").insert(chunk_records).execute()

            # Step 5: Update document status to ready
            self._supabase.table("documents").update(
                {
                    "status": "ready",
                    "metadata": {
                        **extraction_result.metadata,
                        "chunk_count": len(chunks),
                    },
                }
            ).eq("id", document_id).execute()

            logger.info(
                "Document %s processed successfully: %d chunks",
                document_id,
                len(chunks),
            )

        except Exception as exc:
            logger.error("Failed to process document %s: %s", document_id, exc)
            self._supabase.table("documents").update(
                {
                    "status": "error",
                    "metadata": {"error": str(exc)},
                }
            ).eq("id", document_id).execute()
            raise
