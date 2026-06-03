"""Text-to-SQL tool: natural language queries over document metadata (Phase 1: rule-based)."""

from __future__ import annotations
import logging
import re
from typing import Any

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class SQLToolService:
    """Rule-based Text-to-SQL for common document metadata queries."""

    def __init__(self):
        self._supabase = get_supabase_client()

    def execute(self, query: str, user_id: str) -> dict[str, Any]:
        """Parse a natural-language query and execute against the documents table.

        Args:
            query: Natural-language question about documents.
            user_id: Current user's ID.

        Returns:
            Dict with 'results', 'sql_description', and optional 'error'.
        """
        query_lower = query.lower().strip()

        try:
            # Pattern: "how many documents" / "count documents"
            if re.search(r"how many|count|total", query_lower):
                return self._count_documents(user_id, query_lower)

            # Pattern: "list all PDFs" / "show PDFs" / "find PDFs"
            if re.search(r"(list|show|find|get).*(pdf|docx|html|markdown|md)", query_lower):
                return self._filter_by_type(user_id, query_lower)

            # Pattern: "documents uploaded this week/today/yesterday"
            if re.search(r"(this week|today|yesterday|recent|latest|last)", query_lower):
                return self._recent_documents(user_id, query_lower)

            # Pattern: "documents with status error/processing/ready"
            if re.search(r"(status|error|processing|ready|pending|failed)", query_lower):
                return self._filter_by_status(user_id, query_lower)

            # Default: list all documents
            return self._list_all(user_id)

        except Exception as exc:
            logger.error("SQL tool error: %s", exc)
            return {
                "results": [],
                "sql_description": "Error executing query",
                "error": str(exc),
            }

    def _count_documents(self, user_id: str, query: str) -> dict[str, Any]:
        """Count documents, optionally filtered by type."""
        base = self._supabase.table("documents").select("id", count="exact").eq("user_id", user_id)

        # Check if filtering by type
        mime_type = self._extract_mime_type(query)
        if mime_type:
            base = base.eq("mime_type", mime_type)

        result = base.execute()
        count = result.count or 0

        type_label = f" {self._mime_to_label(mime_type)}" if mime_type else ""
        return {
            "results": [{"count": count}],
            "sql_description": f"Count of{type_label} documents",
        }

    def _filter_by_type(self, user_id: str, query: str) -> dict[str, Any]:
        """List documents filtered by MIME type."""
        mime_type = self._extract_mime_type(query)
        if not mime_type:
            return self._list_all(user_id)

        result = (
            self._supabase.table("documents")
            .select("id, filename, mime_type, status, created_at")
            .eq("user_id", user_id)
            .eq("mime_type", mime_type)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "results": result.data,
            "sql_description": f"Documents of type {self._mime_to_label(mime_type)}",
        }

    def _recent_documents(self, user_id: str, query: str) -> dict[str, Any]:
        """List recently uploaded documents."""
        result = (
            self._supabase.table("documents")
            .select("id, filename, mime_type, status, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return {
            "results": result.data,
            "sql_description": "Recently uploaded documents (latest 10)",
        }

    def _filter_by_status(self, user_id: str, query: str) -> dict[str, Any]:
        """List documents filtered by status."""
        status = "ready"
        if "error" in query or "failed" in query:
            status = "error"
        elif "processing" in query:
            status = "processing"
        elif "pending" in query:
            status = "pending"

        result = (
            self._supabase.table("documents")
            .select("id, filename, mime_type, status, created_at, metadata")
            .eq("user_id", user_id)
            .eq("status", status)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "results": result.data,
            "sql_description": f"Documents with status '{status}'",
        }

    def _list_all(self, user_id: str) -> dict[str, Any]:
        """List all user documents."""
        result = (
            self._supabase.table("documents")
            .select("id, filename, mime_type, status, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "results": result.data,
            "sql_description": "All documents",
        }

    @staticmethod
    def _extract_mime_type(query: str) -> str | None:
        """Extract MIME type from query text."""
        if "pdf" in query:
            return "application/pdf"
        if "docx" in query or "word" in query:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if "html" in query:
            return "text/html"
        if "markdown" in query or " md " in query or query.endswith("md"):
            return "text/markdown"
        return None

    @staticmethod
    def _mime_to_label(mime_type: str | None) -> str:
        """Convert MIME type to a human-readable label."""
        labels = {
            "application/pdf": "PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
            "text/html": "HTML",
            "text/markdown": "Markdown",
        }
        return labels.get(mime_type or "", "Unknown")
