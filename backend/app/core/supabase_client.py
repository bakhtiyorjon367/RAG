"""Supabase client singleton (service-role for backend operations)."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get the Supabase client using the service-role key.

    The service-role key bypasses RLS, which is necessary for
    backend operations like ingestion (inserting chunks on behalf of users).
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
