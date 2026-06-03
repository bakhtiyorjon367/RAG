"""Pydantic schemas for chunks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChunkResponse(BaseModel):
    """Response schema for a chunk."""

    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChunkListResponse(BaseModel):
    """Response schema for a paginated list of chunks."""

    chunks: list[ChunkResponse]
    total: int
    page: int
    per_page: int


class SearchResultItem(BaseModel):
    """A single search result."""

    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Request schema for hybrid search."""

    query: str
    top_k: int = 5
    filters: SearchFilters | None = None


class SearchFilters(BaseModel):
    """Filters for search queries."""

    document_ids: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    mime_types: list[str] | None = None


class SearchResponse(BaseModel):
    """Response schema for search results."""

    results: list[SearchResultItem]
    query: str
    total: int
