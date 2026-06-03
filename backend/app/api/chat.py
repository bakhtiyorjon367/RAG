"""Chat API endpoints — RAG with Gemini LLM generation."""

from __future__ import annotations

import json
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.core.auth import get_current_user
from app.models.chunk import SearchRequest, SearchFilters
from app.services.embedding import EmbeddingService
from app.services.search import SearchService
from app.services.llm import LLMService

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_search_service(request: Request) -> SearchService:
    embedding_service: EmbeddingService = request.app.state.embedding_service
    return SearchService(embedding_service)


@router.post("/chat")
async def chat(
    body: dict,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """RAG chat: search documents → build context → stream Gemini answer.

    Request body:
        {
            "query": "What is ...",
            "top_k": 5,          // optional
            "filters": { ... }   // optional
        }

    Returns Server-Sent Events (SSE) stream:
        data: {"type": "sources", "results": [...]}
        data: {"type": "token", "content": "..."}
        data: {"type": "done"}
    """
    query = body.get("query", "").strip()
    if not query:
        return {"error": "Query is required"}

    top_k = body.get("top_k", 5)
    filters_raw = body.get("filters")
    filters = SearchFilters(**filters_raw) if filters_raw else None

    # 1) Retrieve relevant chunks via hybrid search
    search_service = _get_search_service(request)
    results = search_service.search(
        query=query,
        user_id=user_id,
        top_k=top_k,
        filters=filters,
    )

    # Convert to dicts for the LLM service
    chunks_for_llm = [
        {
            "document_name": r.document_name,
            "content": r.content,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in results
    ]

    # Serializable sources to send to the frontend
    sources = [
        {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "document_name": r.document_name,
            "content": r.content,
            "score": r.score,
            "metadata": r.metadata,
        }
        for r in results
    ]

    # 2) Stream the LLM response
    async def event_stream():
        # First, send the source chunks so the frontend can render them
        yield f"data: {json.dumps({'type': 'sources', 'results': sources})}\n\n"

        try:
            llm = LLMService()
            async for token in llm.generate_stream(query, chunks_for_llm):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            logger.exception("LLM generation failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(user_id: str = Depends(get_current_user)):
    """List conversations — Phase 3."""
    return {"conversations": [], "message": "Coming in Phase 3"}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get conversation messages — Phase 3."""
    return {"messages": [], "message": "Coming in Phase 3"}
