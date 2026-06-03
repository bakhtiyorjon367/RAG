"""Search API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.models.chunk import SearchRequest, SearchResponse
from app.services.embedding import EmbeddingService
from app.services.search import SearchService
from app.services.sql_tool import SQLToolService

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_search_service(request: Request) -> SearchService:
    """Get the search service with the app-level embedding service."""
    embedding_service: EmbeddingService = request.app.state.embedding_service
    return SearchService(embedding_service)


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(
    body: SearchRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Hybrid search: vector + keyword + RRF + rerank.

    Returns ranked chunks matching the query.
    """
    search_service = _get_search_service(request)

    results = search_service.search(
        query=body.query,
        user_id=user_id,
        top_k=body.top_k,
        filters=body.filters,
    )
    if settings.SEARCH_DEBUG:
        logger.info(
            "[search] api: query=%r results=%d scores=%s",
            body.query,
            len(results),
            [round(r.score, 4) for r in results],
        )
    return SearchResponse(
        results=results,
        query=body.query,
        total=len(results),
    )


@router.post("/search/sql")
async def text_to_sql(
    body: dict,
    user_id: str = Depends(get_current_user),
):
    """Text-to-SQL: natural language query over document metadata.

    Phase 1: rule-based conversion for common queries.
    """
    query = body.get("query", "")
    if not query:
        return {"error": "Query is required", "results": []}

    sql_service = SQLToolService()
    result = sql_service.execute(query, user_id)
    return result
