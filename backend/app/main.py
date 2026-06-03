"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError

from app.api import documents, search, chat
from app.core.auth import close_http_client
from app.core.config import settings
from app.core.supabase_health import validate_supabase_service_key
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load resources on startup, clean up on shutdown."""
    validate_supabase_service_key()
    embedding_service = EmbeddingService()
    embedding_service.load_model()
    app.state.embedding_service = embedding_service
    yield
    await close_http_client()


app = FastAPI(
    title="RAG Document Search Engine",
    description="Retrieval-Augmented Generation system for document search",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])


@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok"}
