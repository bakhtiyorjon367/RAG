"""Pydantic schemas for documents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response schema for a document."""

    id: str
    user_id: str
    filename: str
    storage_path: str
    mime_type: str
    content_hash: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Response schema for a list of documents."""

    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Response schema after uploading a document."""

    id: str
    filename: str
    status: str
    message: str = "Document uploaded and processing started"


class DocumentDetailResponse(DocumentResponse):
    """Response schema for document detail view with chunk count."""

    chunk_count: int = 0
