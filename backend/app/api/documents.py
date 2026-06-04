"""Document ingestion API endpoints."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.models.chunk import ChunkListResponse, ChunkResponse
from app.models.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.embedding import EmbeddingService
from app.services.ingestion import IngestionService 

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_ingestion_service(request: Request) -> IngestionService:
    """Get the ingestion service with the app-level embedding service."""
    embedding_service: EmbeddingService = request.app.state.embedding_service
    return IngestionService(embedding_service)


@router.post(
    "/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """Upload a file and run the ingestion pipeline synchronously.

    1. Validate file size and type
    2. Compute content hash (dedup check)
    3. Upload to Supabase Storage
    4. Create document record
    5. Run the extract→chunk→embed→store pipeline and wait for it to finish

    All blocking calls (Supabase I/O, extraction, embedding) run off the async
    event loop via ``run_in_executor``, but the request only returns once
    processing has completed and the document row has been flipped to
    ``ready``/``error``. This keeps the UI in sync without relying on realtime
    updates. Trade-off: the request stays open for the full processing time, so
    very large documents can hit the client upload timeout.
    """
    ingestion = _get_ingestion_service(request)

    # Validate MIME type
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Supported types: PDF, DOCX, HTML, Markdown",
        )

    # Read file bytes
    file_bytes = await file.read()

    # Validate file size
    if len(file_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    loop = asyncio.get_event_loop()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"

    # Compute content hash for dedup (fast, CPU-only)
    content_hash = ingestion.compute_content_hash(file_bytes)

    # Check for duplicate (blocking Supabase I/O → run off the event loop)
    existing = await loop.run_in_executor(
        None, partial(ingestion.check_duplicate, user_id, content_hash)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A document with identical content already exists.",
                "existing_document_id": existing["id"],
                "existing_filename": existing["filename"],
            },
        )

    # Upload raw file to storage (blocking I/O → run off the event loop)
    storage_path = await loop.run_in_executor(
        None,
        partial(ingestion.upload_to_storage, user_id, filename, file_bytes, mime_type),
    )

    # Create document record (blocking I/O → run off the event loop)
    doc = await loop.run_in_executor(
        None,
        partial(
            ingestion.create_document_record,
            user_id=user_id,
            filename=filename,
            storage_path=storage_path,
            mime_type=mime_type,
            content_hash=content_hash,
        ),
    )

    # Run the heavy pipeline synchronously, off the event loop. The request
    # waits for extract→chunk→embed→store to finish so the document row is
    # already ``ready``/``error`` by the time the client refetches.
    await loop.run_in_executor(
        None,
        partial(
            ingestion.process_document,
            document_id=doc["id"],
            file_bytes=file_bytes,
            mime_type=mime_type,
            filename=filename,
        ),
    )

    return DocumentUploadResponse(
        id=doc["id"],
        filename=filename,
        status="processing",
        message="Document uploaded and processing started",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(user_id: str = Depends(get_current_user)):
    """List all documents for the current user."""
    supabase = get_supabase_client()
    result = (
        supabase.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    documents = [DocumentResponse(**doc) for doc in result.data]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str, user_id: str = Depends(get_current_user)):
    """Get document details including chunk count."""
    supabase = get_supabase_client()

    # Get document
    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Get chunk count
    chunk_result = (
        supabase.table("chunks")
        .select("id", count="exact")
        .eq("document_id", document_id)
        .execute()
    )

    return DocumentDetailResponse(
        **result.data,
        chunk_count=chunk_result.count or 0,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, user_id: str = Depends(get_current_user)):
    """Delete a document and all its chunks (cascade).

    Also removes the file from Supabase Storage.
    """
    supabase = get_supabase_client()

    # Get document to verify ownership and get storage path
    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    doc = result.data

    # Delete from storage
    try:
        supabase.storage.from_("documents").remove([doc["storage_path"]])
    except Exception as exc:
        logger.warning("Failed to delete file from storage: %s", exc)

    # Delete document row (chunks auto-deleted by CASCADE)
    supabase.table("documents").delete().eq("id", document_id).execute()


@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
async def list_chunks(
    document_id: str,
    page: int = 1,
    per_page: int = 50,
    user_id: str = Depends(get_current_user),
):
    """List chunks for a document (paginated)."""
    supabase = get_supabase_client()

    # Verify document ownership
    doc_result = (
        supabase.table("documents")
        .select("id")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not doc_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Get chunks with pagination
    offset = (page - 1) * per_page
    result = (
        supabase.table("chunks")
        .select("id, document_id, chunk_index, content, token_count, metadata, created_at", count="exact")
        .eq("document_id", document_id)
        .order("chunk_index")
        .range(offset, offset + per_page - 1)
        .execute()
    )

    chunks = [ChunkResponse(**chunk) for chunk in result.data]
    return ChunkListResponse(
        chunks=chunks,
        total=result.count or 0,
        page=page,
        per_page=per_page,
    )
