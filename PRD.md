# PRD — RAG Document Search Engine

> **Version:** 0.2 (Multilingual stack)
> **Last updated:** 2026-02-23
> **Author:** YYSOFT

**source venv/bin/activate uvicorn app.main:app**
---

## 1. Overview

A self-hosted Retrieval-Augmented Generation (RAG) system that lets users **ingest documents**, **search them via natural language**, and (in a later phase) **generate LLM-powered answers** grounded in those documents.

The system exposes **two interfaces**:

| Interface | Purpose |
|-----------|---------|
| **Ingestion UI** | Upload files, monitor processing status, manage documents |
| **Chat UI** | Ask natural-language questions, view ranked chunks (and later, LLM answers) |

**Implemented stack:** Multilingual RAG with 1024-dim embeddings (fastembed: `intfloat/multilingual-e5-large`), character-based chunking, FlashRank reranker (`jinaai/jina-reranker-v2-base-multilingual`). ONNX-only backend (no PyTorch/Transformers).

---

## 2. Core Pipeline

```
┌──────────────┐     ┌────────────┐     ┌────────────────┐     ┌──────────────┐
│  Upload File │────▶│  Extract   │────▶│  Chunk Text    │────▶│  Embed Each  │
│  (Ingestion) │     │  Text      │     │  (split)       │     │  Chunk       │
└──────────────┘     └────────────┘     └────────────────┘     └──────┬───────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │ Store in     │
                                                               │ pgvector     │
                                                               └──────────────┘

┌──────────────┐     ┌────────────┐     ┌────────────────┐     ┌──────────────┐
│  User asks   │────▶│  Embed the │────▶│  Vector Search │────▶│  Rerank &    │
│  a question  │     │  query     │     │  (+ keyword)   │     │  Return      │
└──────────────┘     └────────────┘     └────────────────┘     └──────┬───────┘
                                                                      │
                                                          ┌───────────┴────────────--┐
                                                          │ /chat does both: return  │
                                                          │ ranked chunks + stream   │
                                                          │ LLM answer (RAG)         │
                                                          └────────────────────────--┘
```

### Step-by-step

| # | Step | Detail |
|---|------|--------|
| 1 | **Extract text** | Parse uploaded file (PDF, DOCX, HTML, Markdown) into plain text using `docling`. |
| 2 | **Chunk** | Split extracted text into overlapping chunks (character-based: default 512 characters, 50-character overlap). |
| 3 | **Embed** | Generate a 1024-dim vector for each chunk using **fastembed** (ONNX). Default model: `intfloat/multilingual-e5-large` (multilingual). Query/passage prefixes applied for E5. |
| 4 | **Store** | Persist chunk text, embedding vector, and metadata in Supabase PostgreSQL with the `pgvector` extension. |
| 5 | **Query** | User submits a question → embed the query with the same model. |
| 6 | **Retrieve** | Hybrid search: cosine-similarity vector search **+** keyword (full-text) search → fuse results. |
| 7 | **Rerank** | Score and reorder candidates (e.g.  Flashrank). |
| 8 | **Return** | Return the top-K ranked chunks with source metadata to the user. |
| 9 | **Generate** | Send top chunks + question to an LLM → return a grounded, cited answer (streaming). The main Chat flow via `POST /api/v1/chat` already does steps 5–9 in one request. |

---

## 3. Scope

### 3.1 In Scope

- Document ingestion and processing pipeline
- Multi-format support: **PDF, DOCX, HTML, Markdown**
- Text extraction via **docling**
- Chunking with configurable size and overlap
- Embedding generation (local)
- Vector storage and search with **pgvector**
- Hybrid search (keyword full-text search + vector similarity)
- Reranking of search results
- Metadata extraction (filename, page number, headings, dates)
- Record management and deduplication (content-hash based)
- Cascade deletes (delete document → delete all its chunks)
- File storage via **Supabase Storage**
- Authentication via **Supabase Auth**
- Text-to-SQL tool (natural-language queries over structured metadata)
- Two UIs: **Ingestion** and **Chat**

### 3.2 Out of Scope

- Knowledge graphs / GraphRAG
- Code execution / sandboxing
- Image / audio / video processing
- Model fine-tuning
- Multi-tenant admin features
- Billing / payments
- Data connectors (Google Drive, SFTP, external APIs, webhooks)
- Scheduled / automated ingestion
- Admin UI (configuration via environment variables only)

---

## 4. Tech Stack

| Layer | Choice |
|-------|--------|
| **Frontend** | React + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| **Backend** | Python 3.11+ + FastAPI |
| **Database** | Supabase PostgreSQL + pgvector extension |
| **Auth** | Supabase Auth (JWT) |
| **File Storage** | Supabase Storage (buckets) |
| **Realtime** | Supabase Realtime (ingestion status updates) |
| **Text Extraction** | docling (or pymupdf + python-docx + beautifulsoup4) |
| **Embeddings** | fastembed (ONNX, local; e.g. `intfloat/multilingual-e5-large`, 1024-dim) — no PyTorch/Transformers |
| **Reranking** | FlashRank (ONNX, local; e.g. `jinaai/jina-reranker-v2-base-multilingual`) |

---

## 5. Data Model

### 5.1 `documents`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → auth.users | Owner |
| `filename` | `text` | Original filename |
| `storage_path` | `text` | Path in Supabase Storage |
| `mime_type` | `text` | e.g. `application/pdf` |
| `content_hash` | `text` UNIQUE | SHA-256 of raw file bytes (dedup) |
| `status` | `enum` | `pending` · `processing` · `ready` · `error` |
| `metadata` | `jsonb` | Extracted metadata (page count, title, etc.) |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

### 5.2 `chunks`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` PK | |
| `document_id` | `uuid` FK → documents (CASCADE DELETE) | |
| `chunk_index` | `int` | Order within document |
| `content` | `text` | Raw chunk text |
| `embedding` | `vector(1024)` | Matches multilingual embedding model (e.g. E5-large) |
| `token_count` | `int` | Character count per chunk (for compatibility) |
| `metadata` | `jsonb` | Page number, heading, section, etc. |
| `created_at` | `timestamptz` | |

**Indexes:**
- `chunks_embedding_idx` — IVFFlat or HNSW index on `embedding` column for vector search
- `chunks_content_fts_idx` — GIN index on `to_tsvector('english', content)` for full-text keyword search

### 5.3 `conversations` *(Phase 2)*

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → auth.users | |
| `title` | `text` | Auto-generated or user-set |
| `created_at` | `timestamptz` | |

### 5.4 `messages` *(Phase 2)*

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` PK | |
| `conversation_id` | `uuid` FK → conversations | |
| `role` | `enum` | `user` · `assistant` |
| `content` | `text` | |
| `sources` | `jsonb` | Array of chunk references |
| `created_at` | `timestamptz` | |

---

## 6. API Design (Backend — FastAPI)

### 6.1 Ingestion Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload file → triggers ingestion pipeline |
| `GET` | `/api/v1/documents` | List user's documents (with status) |
| `GET` | `/api/v1/documents/{id}` | Get document details + chunk count |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + cascade delete chunks |
| `GET` | `/api/v1/documents/{id}/chunks` | List chunks for a document (paginated) |

### 6.2 Search / Chat Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/search` | Hybrid search: accepts `query`, returns ranked chunks |
| `POST` | `/api/v1/search/sql` | Text-to-SQL: natural language → SQL over metadata |

### 6.3 Chat (RAG + conversations)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat` | **Implemented.** RAG chat: query + hybrid retrieval + LLM generation (streaming). |
| `GET` | `/api/v1/conversations` | List conversations *(Phase 3)* |
| `GET` | `/api/v1/conversations/{id}` | Get conversation messages *(Phase 3)* |

All endpoints require a valid Supabase JWT in the `Authorization: Bearer <token>` header.

---

## 7. Frontend Interfaces

### 7.1 Ingestion UI (`/ingest`)

- **File upload** area (drag-and-drop + file picker)
- Supported formats shown: PDF, DOCX, HTML, MD
- **Document list** — table with columns: name, format, status, chunk count, date
- Real-time status updates via Supabase Realtime (`pending → processing → ready`)
- **Delete** button per document (with confirmation)
- Deduplication: warn if file with same content hash already exists

### 7.2 Chat UI (`/chat`)

- Full-width chat interface with a single input bar that calls `POST /api/v1/chat` only.
- The chat endpoint returns **both** ranked source chunks (for cards) and a **streamed LLM answer** in one flow (SSE: sources event, then token events, then done).
- Each source card shows: snippet, document name, page/section, relevance score; click to expand full chunk text.
- Filters: search within specific documents, date range, format type (sent in the request body).
- **Note:** `POST /api/v1/search` exists for raw hybrid search (e.g. API clients) but is not used by the current Chat UI.

---

## 8. Ingestion Pipeline Detail

```
File Upload
    │
    ▼
Supabase Storage (persist raw file)
    │
    ▼
Compute content_hash (SHA-256)
    │
    ├── hash exists? → reject (duplicate) or update
    │
    ▼
Create `documents` row (status = processing)
    │
    ▼
docling: extract text from file
    │
    ▼
Chunking (recursive character splitter, ~512 characters, ~50 overlap)
    │
    ▼
Batch embed all chunks
    │
    ▼
Bulk insert into `chunks` table
    │
    ▼
Update `documents` status → ready
    │
    ▼
Broadcast status via Supabase Realtime
```

**Error handling:** If any step fails, set `documents.status = error` and store the error message in `documents.metadata.error`.

---

## 9. Search / Retrieval Detail

### 9.1 Hybrid Search

1. **Vector search:** Embed query → cosine similarity against `chunks.embedding` → top 20 candidates.
2. **Keyword search:** Full-text search with `ts_rank` against `chunks.content` → top 20 candidates.
3. **Fusion:** Reciprocal Rank Fusion (RRF) to merge both result sets.
4. **Rerank:** Pass fused candidates through a Flashrank reranker → return top K (default 5).

### 9.2 Text-to-SQL

- Accepts a natural language query about document metadata.
- Converts to SQL using rule-based for Phase 1.
- Executes against the `documents` table (read-only, parameterized).
- Returns structured results.

---

## 10. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Max file size** | 50 MB per upload |
| **Supported formats** | PDF, DOCX, HTML, Markdown |
| **Ingestion latency** | < 30s for a 20-page PDF |
| **Search latency** | < 2s end-to-end (embed + search + rerank) |
| **Concurrent users** | Single-user to start; Supabase Auth supports multi-user |
| **Embedding dimensions** | 1024 (multilingual stack; configurable via `EMBEDDING_DIM`) |
| **Chunk size** | Configurable via env vars (default 512 **characters**, 50-character overlap) |
| **Auth** | Supabase Auth (email/password, OAuth optional) |
| **Deployment** | Docker Compose (frontend + backend + Supabase) |

---

## 11. Configuration (Environment Variables)

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | — |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | — |
| `SUPABASE_SERVICE_KEY` | Supabase service-role key | — |
| `EMBEDDING_MODEL` | fastembed model name (e.g. multilingual E5) | `intfloat/multilingual-e5-large` |
| `EMBEDDING_DIM` | Embedding vector dimension | `1024` |
| `CHUNK_SIZE` | Target chunk size in **characters** | `512` |
| `CHUNK_OVERLAP` | Overlap between chunks in **characters** | `50` |
| `RERANK_MODEL` | FlashRank model name or `none` | `jinaai/jina-reranker-v2-base-multilingual` |
| `MAX_UPLOAD_SIZE_MB` | Max file upload size | `50` |
| `TOP_K` | Default number of results to return | `5` |

---

## 12. Project Structure (Proposed)

```
RAG/
├── frontend/                  # React + Vite app
│   ├── src/
│   │   ├── components/        # Shared UI components (shadcn/ui)
│   │   ├── pages/
│   │   │   ├── Ingest.tsx     # Ingestion UI
│   │   │   └── Chat.tsx       # Chat / Search UI
│   │   ├── lib/               # API client, Supabase client, utils
│   │   ├── hooks/             # Custom React hooks
│   │   └── App.tsx
│   ├── index.html
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                   # FastAPI app
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── documents.py   # Ingestion endpoints
│   │   │   ├── search.py      # Search endpoints
│   │   │   └── chat.py        # RAG chat endpoint (implemented)
│   │   ├── core/
│   │   │   ├── config.py      # Settings from env vars
│   │   │   └── auth.py        # Supabase JWT validation
│   │   ├── services/
│   │   │   ├── ingestion.py   # Extract → chunk → embed → store
│   │   │   ├── extraction.py  # docling text extraction
│   │   │   ├── chunking.py    # Text splitting logic
│   │   │   ├── embedding.py   # Embedding model wrapper
│   │   │   ├── search.py      # Hybrid search + rerank
│   │   │   └── sql_tool.py    # Text-to-SQL
│   │   └── models/
│   │       ├── document.py    # Pydantic schemas
│   │       └── chunk.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── supabase/                  # Supabase config & migrations
│   └── migrations/
│       ├── 001_init.sql       # Tables, indexes, RLS policies
│       └── 002_bilingual_embeddings_1024.sql  # Upgrade chunks.embedding to vector(1024)
│
├── docker-compose.yml
├── .env.example
├── PRD.md                     # ← This document
└── README.md
```

---

## 13. Open Questions

| # | Question | Notes |
|---|----------|-------|
| 1 | **Local vs API embeddings?** | Implemented: local **fastembed** (ONNX, e.g. multilingual-e5-large). No PyTorch/Transformers. |
| 2 | **Reranker choice?** | FlashRank (ONNX, local); default `jinaai/jina-reranker-v2-base-multilingual` for Korean/English. |
| 3 | **Chunk size tuning?** | 512 **characters** default (character-based for multilingual models); configurable via env. |
| 4 | **Ingestion: sync vs async?** | Small files could be sync; large files should be async with status polling / Realtime. |
| 5 | **Multi-user from day 1?** | Supabase Auth + RLS enables this cheaply. Recommend yes. |
| 6 | **Self-hosted Supabase vs cloud?** | Docker Compose for local dev; cloud Supabase for deploy? |
