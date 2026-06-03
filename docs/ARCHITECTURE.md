# Search, SQL tool, and Chat — how they work

This document describes how the backend search pipeline, SQL tool, and chat API relate to each other.

---

## Search service (`backend/app/services/search.py`)

- **Role:** Hybrid retrieval over document chunks (content search).
- **Flow:** Embed query → vector search + keyword (FTS) search → RRF fusion → rerank → return `SearchResultItem` list.
- **Used by:** Both the Search API and the Chat API (chat uses it for RAG context).

---

## Search API (`backend/app/api/search.py`)

- **`POST /api/v1/search`** — Runs the search service and returns raw ranked chunks (no LLM). For API clients that want retrieval only.
- **`POST /api/v1/search/sql`** — Text-to-SQL: natural language → rule-based mapping → queries the `documents` table (metadata: count, type, status, recent). Returns structured results; not used by the Chat UI.

The **Chat UI uses only `/chat`**; it does not call `/search` or `/search/sql`.

---

## SQL tool (`backend/app/services/sql_tool.py`)

- **Role:** Rule-based “text-to-SQL” over document **metadata** (e.g. “how many PDFs?”, “list documents with errors”).
- **Triggered by:** `POST /api/v1/search/sql` only. Not used in the main Chat flow.

---

## Chat API (`backend/app/api/chat.py`)

- **Role:** Single RAG path: retrieve chunks, then generate an answer.
- **Flow:**
  1. Call `SearchService.search()` (same hybrid search as above) with the user query.
  2. Send top chunks as context to `LLMService.generate_stream()`.
  3. Return SSE stream: `sources` event (chunk cards), then `token` events (streamed answer), then `done`.
- **Conversation persistence** (list conversations, load history) is planned for Phase 3; the streaming RAG response is already implemented.
