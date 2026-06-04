"""Application settings loaded from environment variables."""

from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration from PRD Section 11."""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str = ""  # No longer required; auth uses Supabase API

    # Embedding (multilingual E5-base: 768-dim, ONNX via fastembed)
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"
    EMBEDDING_DIM: int = 768
    FASTEMBED_CACHE_PATH: str = ""  # If set, applied to os.environ before loading model

    # Chunking (character-based for BGE-M3; CHUNK_SIZE/OVERLAP in characters)
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Ingestion (memory-bounded processing for low-RAM instances)
    # Embed + insert chunks in small batches so peak memory stays flat
    # regardless of document size. INGEST_BATCH_SIZE = chunks per batch.
    # EMBED_PARALLEL = fastembed worker processes. <=1 runs fully in-process
    # (safest on low-memory/containerized hosts; fastembed only avoids its
    # multiprocessing worker pool when parallel is None). >1 spawns that many
    # subprocesses, which can be OOM-killed or fail to spawn in constrained
    # containers, so keep it at 1 unless you have headroom.

    INGEST_BATCH_SIZE: int = 16
    EMBED_PARALLEL: int = 1

    # Reranking (FlashRank). Must be a name from FlashRank's model zoo, e.g.
    # ms-marco-MultiBERT-L-12 (multilingual, KO/EN), ms-marco-MiniLM-L-12-v2
    # (English), ms-marco-TinyBERT-L-2-v2 (tiny/fast), or "none" to disable.
    RERANK_MODEL: str = "ms-marco-MultiBERT-L-12"
    # Persisted cache dir for the reranker so it isn't re-downloaded each restart.
    RERANK_CACHE_PATH: str = "/app/.flashrank_cache"

    # Search
    TOP_K: int = 5
    VECTOR_SIMILARITY_THRESHOLD: float = 0.6  # Min cosine similarity for vector search (DB + Python filter)
    SEARCH_SCORE_THRESHOLD: float = 0.5  # Minimum relevance score (0-1) after rerank to include a result
    MAX_CHUNKS_PER_DOCUMENT: int = 3  # Max chunks per document in results (0 = no cap)
    SEARCH_NO_OVERLAP_PENALTY: float = 0.5  # Multiply score by this when chunk has no query-term overlap (0 = disabled)
    SEARCH_DEBUG: bool = False  # When True, log pipeline stats at INFO (query, counts, score ranges, dropped)

    # LLM (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def allowed_mime_types(self) -> set[str]:
        return {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/html",
            "text/markdown",
            "text/x-markdown",
            "text/plain",
        }

    model_config = {
        "env_file": ("../.env", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]
