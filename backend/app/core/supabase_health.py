"""Validate Supabase credentials at startup."""

from __future__ import annotations

import logging

from postgrest.exceptions import APIError

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def validate_supabase_service_key() -> None:
    """Fail fast if the service role key does not match SUPABASE_URL."""
    client = get_supabase_client()
    try:
        client.table("documents").select("id").limit(1).execute()
    except APIError as exc:
        details = str(exc)
        if "Invalid API key" in details or "401" in details:
            raise RuntimeError(
                "Supabase rejected SUPABASE_SERVICE_KEY (Invalid API key). "
                "Copy the service_role / secret key from the SAME project as "
                "SUPABASE_URL in Settings → API, then restart the backend."
            ) from exc
        # Table missing — migrations not applied yet
        if "PGRST205" in details or "does not exist" in details.lower():
            logger.warning(
                "Supabase connected but 'documents' table not found. "
                "Run supabase/migrations/001_init.sql in the SQL Editor."
            )
            return
        raise
