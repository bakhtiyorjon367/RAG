"""Text chunking with configurable size and overlap (character-based for BGE-M3)."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with metadata."""

    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ChunkingService:
    """Recursive character text splitter with character-based sizing (BGE-M3 compatible)."""

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        # CHUNK_SIZE and CHUNK_OVERLAP are character counts (safe for BGE-M3 8192 token limit)
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def _char_count(self, text: str) -> int:
        """Return character length (stored as token_count for DB compatibility)."""
        return len(text)

    def split(self, text: str, doc_metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text into overlapping chunks.

        Args:
            text: The full document text.
            doc_metadata: Optional metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text, self.SEPARATORS)
        merged = self._merge_chunks(raw_chunks)

        chunks: list[Chunk] = []
        for i, content in enumerate(merged):
            char_count = self._char_count(content)
            metadata = dict(doc_metadata) if doc_metadata else {}
            metadata["chunk_index"] = i
            chunks.append(
                Chunk(
                    chunk_index=i,
                    content=content,
                    token_count=char_count,
                    metadata=metadata,
                )
            )

        logger.info("Split text into %d chunks", len(chunks))
        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using a hierarchy of separators."""
        if not separators:
            return [text] if text.strip() else []

        separator = separators[0]
        remaining_separators = separators[1:]

        if not separator:
            # Last resort: split by characters
            return [
                text[i : i + self.chunk_size * 4]
                for i in range(0, len(text), self.chunk_size * 4)
            ]

        parts = text.split(separator)
        result: list[str] = []

        for part in parts:
            if not part.strip():
                continue
            char_count = self._char_count(part)
            if char_count <= self.chunk_size:
                result.append(part.strip())
            else:
                sub_parts = self._recursive_split(part, remaining_separators)
                result.extend(sub_parts)

        return result

    def _merge_chunks(self, parts: list[str]) -> list[str]:
        """Merge small parts into chunks respecting size and overlap (character-based)."""
        if not parts:
            return []

        merged: list[str] = []
        current_parts: list[str] = []
        current_chars = 0

        for part in parts:
            part_chars = self._char_count(part)

            if current_chars + part_chars > self.chunk_size and current_parts:
                merged.append("\n\n".join(current_parts))

                overlap_parts: list[str] = []
                overlap_chars = 0
                for p in reversed(current_parts):
                    p_chars = self._char_count(p)
                    if overlap_chars + p_chars > self.chunk_overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_chars += p_chars

                current_parts = overlap_parts
                current_chars = overlap_chars

            current_parts.append(part)
            current_chars += part_chars

        if current_parts:
            merged.append("\n\n".join(current_parts))

        return merged
