"""Text extraction from documents using lightweight libraries.

- PDF: PyMuPDF (fitz)
- DOCX: python-docx
- HTML: BeautifulSoup4
- Markdown: read as-is
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Result of text extraction from a document."""

    def __init__(self, text: str, metadata: dict[str, Any]):
        self.text = text
        self.metadata = metadata


class ExtractionService:
    """Extract text from various document formats."""

    SUPPORTED_EXTENSIONS = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/html": ".html",
        "text/markdown": ".md",
        "text/x-markdown": ".md",
        "text/plain": ".txt",
    }

    def extract(self, file_bytes: bytes, mime_type: str, filename: str) -> ExtractionResult:
        """Extract text and metadata from a document.

        Args:
            file_bytes: Raw file content.
            mime_type: MIME type of the document.
            filename: Original filename.

        Returns:
            ExtractionResult with text and metadata.
        """
        if mime_type not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported MIME type: {mime_type}")

        metadata: dict[str, Any] = {
            "filename": filename,
            "mime_type": mime_type,
        }

        if mime_type == "application/pdf":
            text, pdf_meta = self._extract_pdf(file_bytes)
            metadata.update(pdf_meta)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text, docx_meta = self._extract_docx(file_bytes)
            metadata.update(docx_meta)
        elif mime_type == "text/html":
            text = self._extract_html(file_bytes)
        elif mime_type in ("text/markdown", "text/x-markdown", "text/plain"):
            text = file_bytes.decode("utf-8", errors="replace")
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")

        logger.info("Extracted text from %s: %d chars", filename, len(text))
        return ExtractionResult(text=text, metadata=metadata)

    def _extract_pdf(self, file_bytes: bytes) -> tuple[str, dict[str, Any]]:
        """Extract text from PDF using PyMuPDF4LLM (Markdown output for LLM/RAG)."""
        import fitz  # pymupdf
        import pymupdf4llm

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        metadata: dict[str, Any] = {
            "page_count": len(doc),
        }
        pdf_meta = doc.metadata
        if pdf_meta:
            if pdf_meta.get("title"):
                metadata["title"] = pdf_meta["title"]
            if pdf_meta.get("author"):
                metadata["author"] = pdf_meta["author"]

        text = pymupdf4llm.to_markdown(doc)
        doc.close()
        return text, metadata

    def _extract_docx(self, file_bytes: bytes) -> tuple[str, dict[str, Any]]:
        """Extract text from DOCX using python-docx."""
        import io
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        metadata: dict[str, Any] = {
            "paragraph_count": len(paragraphs),
        }

        # Extract core properties if available
        if doc.core_properties:
            if doc.core_properties.title:
                metadata["title"] = doc.core_properties.title
            if doc.core_properties.author:
                metadata["author"] = doc.core_properties.author

        return "\n\n".join(paragraphs), metadata

    def _extract_html(self, file_bytes: bytes) -> str:
        """Extract text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(file_bytes, "lxml")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text
