# Progress — RAG Document Search Engine

> **Last updated:** 2026-02-10

---

## Phase 1: Foundation (MVP) — ✅ Complete

All 18 implementation steps from Plan 1 have been executed.

### Tasks Completed

| # | Task | Status |
|---|------|--------|
| 1 | Project scaffolding (frontend + backend dirs, configs) | ✅ Done |
| 2 | Docker Compose + `.env.example` | ✅ Done |
| 3 | Supabase migration: schema, pgvector, indexes, RLS | ✅ Done |
| 4 | Supabase Storage bucket setup (documented in migration) | ✅ Done |
| 5 | Backend: `config.py`, `auth.py` (JWT validation) | ✅ Done |
| 6 | Backend: `extraction.py` (docling) | ✅ Done |
| 7 | Backend: `chunking.py` | ✅ Done |
| 8 | Backend: `embedding.py` | ✅ Done |
| 9 | Backend: `ingestion.py` (orchestrator) | ✅ Done |
| 10 | Backend: `documents.py` API (upload, list, get, delete, chunks) | ✅ Done |
| 11 | Backend: `search.py` service (hybrid search + RRF + rerank) | ✅ Done |
| 12 | Backend: `search.py` API endpoints | ✅ Done |
| 13 | Backend: `sql_tool.py` (rule-based Text-to-SQL) | ✅ Done |
| 14 | Frontend: Supabase client, API client, auth context | ✅ Done |
| 15 | Frontend: Login / Signup pages | ✅ Done |
| 16 | Frontend: Ingestion UI (upload + document list + realtime) | ✅ Done |
| 17 | Frontend: Chat UI — search mode (query + result cards) | ✅ Done |
| 18 | TypeScript type-check passes (zero errors) | ✅ Done |

### Files Created / Modified

#### Backend (`backend/`)
- `requirements.txt` — Python dependencies
- `Dockerfile` — Docker image for the backend
- `app/main.py` — FastAPI entry point with CORS and lifespan
- `app/core/config.py` — Pydantic Settings from env vars
- `app/core/auth.py` — Supabase JWT validation dependency
- `app/core/supabase_client.py` — Supabase client singleton (service-role)
- `app/models/document.py` — Document Pydantic schemas
- `app/models/chunk.py` — Chunk and search Pydantic schemas
- `app/services/extraction.py` — Text extraction via docling
- `app/services/chunking.py` — Recursive character text splitter with tiktoken
- `app/services/embedding.py` — Embedding service (local + OpenAI)
- `app/services/ingestion.py` — Ingestion orchestrator (extract → chunk → embed → store)
- `app/services/search.py` — Hybrid search (vector + keyword + RRF + rerank)
- `app/services/sql_tool.py` — Rule-based Text-to-SQL
- `app/api/documents.py` — Document CRUD endpoints
- `app/api/search.py` — Search + SQL tool endpoints
- `app/api/chat.py` — RAG chat (hybrid search → LLM streaming); conversation history is Phase 3

#### Frontend (`frontend/`)
- Scaffolded with Vite + React + TypeScript
- Tailwind CSS v4 with `@tailwindcss/vite` plugin
- shadcn/ui initialized with 14 components
- `src/lib/supabase.ts` — Supabase client
- `src/lib/api.ts` — Axios API wrapper with JWT auto-attach
- `src/hooks/useAuth.tsx` — Auth context provider
- `src/components/layout/AppLayout.tsx` — App shell with navigation
- `src/components/layout/ProtectedRoute.tsx` — Route guard
- `src/pages/Login.tsx` — Login page
- `src/pages/Signup.tsx` — Signup page with email verification
- `src/pages/Ingest.tsx` — Ingestion UI (drag-drop upload, document table, realtime status, delete)
- `src/pages/Chat.tsx` — Search UI (query input, filters panel, ranked chunk cards with expand)
- `src/App.tsx` — Router setup

#### Infrastructure
- `docker-compose.yml` — Frontend, backend, Supabase DB
- `.env.example` — All environment variables
- `supabase/migrations/001_init.sql` — Full schema (documents, chunks, pgvector, HNSW index, FTS index, RLS policies, RPC functions for vector/keyword search)

### Deviations from Plan

- **None** — All plan items were implemented as specified.

---

## Phase 2: LLM Generation — 🔜 Pending

See `.agent/plans/plan2.md`

## Phase 3: Polish & Scale — 🔜 Pending

See `.agent/plans/plan3.md`
