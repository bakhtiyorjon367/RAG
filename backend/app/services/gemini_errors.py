"""Map Google Gemini / google-genai SDK errors to user-facing messages."""

from __future__ import annotations

from typing import Any

GEMINI_QUOTA_EXCEEDED = "gemini_quota_exceeded"
GEMINI_RATE_LIMITED = "gemini_rate_limited"
GEMINI_AUTH_ERROR = "gemini_auth_error"
GEMINI_CONFIG_ERROR = "gemini_config_error"
LLM_ERROR = "llm_error"


def _text_from_exception(exc: Exception) -> str:
    parts: list[str] = []
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message.strip():
        parts.append(message)
    parts.append(str(exc))
    return " ".join(parts).lower()


def _details_blob(exc: Exception) -> str:
    details = getattr(exc, "details", None)
    if details is None:
        return ""
    if isinstance(details, dict):
        try:
            import json

            return json.dumps(details).lower()
        except (TypeError, ValueError):
            return str(details).lower()
    return str(details).lower()


def _is_free_tier_quota(text: str) -> bool:
    markers = (
        "free_tier",
        "free tier",
        "quota exceeded",
        "resource_exhausted",
        "generaterequestsperday",
        "generate_content_free_tier",
    )
    return any(m in text for m in markers)


def classify_gemini_error(exc: Exception) -> dict[str, Any]:
    """Return a structured error payload for SSE / API responses."""
    from google.genai import errors as genai_errors

    if isinstance(exc, ValueError) and "GEMINI_API_KEY" in str(exc):
        return {
            "code": GEMINI_CONFIG_ERROR,
            "message": (
                "Gemini API key is not configured on the server. "
                "Set GEMINI_API_KEY to enable chat answers."
            ),
        }

    if isinstance(exc, genai_errors.ClientError):
        combined = f"{_text_from_exception(exc)} {_details_blob(exc)}"
        if exc.code == 429:
            if _is_free_tier_quota(combined):
                return {
                    "code": GEMINI_QUOTA_EXCEEDED,
                    "message": (
                        "Gemini free tier quota is exhausted. Daily or per-minute request "
                        "limits have been reached. Please wait for the quota to reset, or "
                        "upgrade your plan at Google AI Studio. Search still works without AI answers."
                    ),
                }
            return {
                "code": GEMINI_RATE_LIMITED,
                "message": (
                    "Gemini rate limit reached. Please wait a minute and try again."
                ),
            }
        if exc.code == 401:
            return {
                "code": GEMINI_AUTH_ERROR,
                "message": (
                    "Gemini API key is invalid or unauthorized. "
                    "Check the server GEMINI_API_KEY configuration."
                ),
            }
        if exc.code == 403:
            return {
                "code": GEMINI_AUTH_ERROR,
                "message": (
                    "Gemini API access denied. The API key may lack permission for this model."
                ),
            }

    combined = f"{_text_from_exception(exc)} {_details_blob(exc)}"
    if "429" in combined and _is_free_tier_quota(combined):
        return {
            "code": GEMINI_QUOTA_EXCEEDED,
            "message": (
                "Gemini free tier quota is exhausted. Daily or per-minute request "
                "limits have been reached. Please wait for the quota to reset, or "
                "upgrade your plan at Google AI Studio. Search still works without AI answers."
            ),
        }

    return {
        "code": LLM_ERROR,
        "message": "Failed to generate an AI answer. Please try again later.",
    }
