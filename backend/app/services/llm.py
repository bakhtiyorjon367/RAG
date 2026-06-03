"""LLM service — sends retrieved context + user question to Google Gemini."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── System prompt for RAG ────────────────────────────────────

RAG_SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions based on the provided document excerpts.

RULES:
1. Base your answer ONLY on the provided context. Do not make up information.
2. If the context does not contain enough information to answer, say so honestly.
3. When referencing information, mention the source document name.
4. Be concise but thorough.
5. Use markdown formatting for readability (headings, bullets, bold, etc.).
"""


def _build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for the prompt."""
    if not chunks:
        return "No relevant documents were found."

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("document_name", "Unknown")
        content = chunk.get("content", "")
        score = chunk.get("score", 0)
        meta = chunk.get("metadata", {})

        header = f"[Source {i}: {doc_name}"
        if meta.get("page") is not None:
            header += f", Page {meta['page']}"
        header += f" | relevance: {score:.0%}]"

        parts.append(f"{header}\n{content}")

    return "\n\n---\n\n".join(parts)


def _build_user_message(question: str, chunks: list[dict]) -> str:
    """Build the user message with context and question."""
    context = _build_context_block(chunks)

    return (
        f"## Retrieved Document Excerpts\n\n{context}\n\n"
        f"---\n\n"
        f"## User Question\n\n{question}"
    )


class LLMService:
    """Thin wrapper around the Google Gen AI SDK (Gemini)."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/"
            )
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL

    # ── Streaming response ────────────────────────────────────

    async def generate_stream(
        self,
        question: str,
        chunks: list[dict],
    ) -> AsyncIterator[str]:
        """Stream the LLM response token-by-token (SSE-friendly)."""
        user_message = _build_user_message(question, chunks)

        stream = await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=RAG_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
