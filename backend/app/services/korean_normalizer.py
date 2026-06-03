"""Korean text normalization for FTS using MeCab-ko (stems + content words)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded MeCab instance
_mecab: Any = None


def _get_mecab() -> Any | None:
    global _mecab
    if _mecab is not None:
        return _mecab
    try:
        from mecab import MeCab
        _mecab = MeCab()
        return _mecab
    except ImportError:
        logger.warning(
            "python-mecab-ko not installed; Korean FTS normalization disabled. "
            "Install with: pip install python-mecab-ko"
        )
        return None
    except Exception as exc:
        logger.warning("MeCab-ko failed to load: %s", exc)
        return None


# POS tag prefixes we keep for keyword search (content words; drop particles/endings)
_CONTENT_POS_PREFIXES = ("N", "V", "M")
_CONTENT_POS_EXACT = ("SL", "SN")  # foreign, number


def normalize_for_fts(text: str) -> str:
    """Normalize Korean text for full-text search: content words only, space-separated.

    Uses MeCab-ko to tokenize and keep nouns (N), verbs (V), modifiers (M), etc.,
    dropping particles (J) and endings (E) so that e.g. '사무실을 이전할' matches '사무실 이전'.
    If MeCab is unavailable, returns the original text.
    """
    if not text or not text.strip():
        return text
    mecab = _get_mecab()
    if mecab is None:
        return text
    try:
        pairs = mecab.pos(text.strip())
        tokens = [
            word for word, pos in pairs
            if pos and (pos.startswith(_CONTENT_POS_PREFIXES) or pos in _CONTENT_POS_EXACT)
        ]
        return " ".join(tokens).strip() if tokens else text.strip()
    except Exception as exc:
        logger.debug("Korean normalization failed for %r: %s", text[:50], exc)
        return text
