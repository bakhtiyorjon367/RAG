-- ============================================================
-- RAG Document Search Engine — Full Migration (E5-Base Edition)
-- ============================================================

-- 1. Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Cleanup (Ensure we start fresh for 768 dimensions)
DROP FUNCTION IF EXISTS match_chunks(vector, int, uuid, uuid[]);
DROP FUNCTION IF EXISTS match_chunks(vector, integer, uuid, uuid[], float);
DROP FUNCTION IF EXISTS keyword_search_chunks(text, int, uuid, uuid[]);

-- Old projects may have documents/chunks without user_id. CREATE TABLE IF NOT EXISTS
-- would skip recreation and later steps fail with: column "user_id" does not exist.
-- This drops app tables only (not auth.users). Comment out if you must keep data
-- and use 003_add_documents_user_id.sql instead.
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- 3. Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'ready', 'error')),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT documents_user_content_hash_unique UNIQUE (user_id, content_hash)
);

CREATE INDEX IF NOT EXISTS documents_user_id_idx ON documents(user_id);
CREATE INDEX IF NOT EXISTS documents_content_hash_idx ON documents(content_hash);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documents_updated_at ON documents;
CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. Chunks table (768-dim for multilingual-e5-base)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    token_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW Index for 768 dimensions
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Keyword Search Index
CREATE INDEX IF NOT EXISTS chunks_content_fts_idx
    ON chunks USING gin (to_tsvector('simple', content));

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_document_chunk_idx ON chunks(document_id, chunk_index);

-- 5. Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users can view their own documents" ON documents FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "Users can insert their own documents" ON documents FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "Users can update their own documents" ON documents FOR UPDATE USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "Users can delete their own documents" ON documents FOR DELETE USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Users can view chunks of their documents" ON chunks FOR SELECT 
    USING (document_id IN (SELECT id FROM documents WHERE user_id = auth.uid()));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "Service role can manage chunks" ON chunks FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 6. RPC: Semantic Search (match_chunks)
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(768),
    match_count int DEFAULT 10,
    p_user_id uuid DEFAULT NULL,
    p_document_ids uuid[] DEFAULT NULL,
    p_threshold float DEFAULT 0.5 -- Default threshold
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    chunk_index int,
    content text,
    token_count int,
    metadata jsonb,
    created_at timestamptz,
    similarity float,
    document_name text,
    filename text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.content,
        c.token_count,
        c.metadata,
        c.created_at,
        1 - (c.embedding <=> query_embedding) AS similarity,
        d.filename AS document_name,
        d.filename
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.user_id = p_user_id
      AND d.status = 'ready'
      AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
      AND (1 - (c.embedding <=> query_embedding)) > p_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 7. RPC: Keyword Search (keyword_search_chunks)
-- Korean FTS: add normalized content column and use it in keyword search.
-- Normalization (MeCab-ko) is done in the app at ingestion and at query time.

-- 1. Add column for MeCab-normalized text (content words only)
ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS content_normalized TEXT;

-- 2. Replace FTS index to search over normalized content when present
DROP INDEX IF EXISTS chunks_content_fts_idx;
CREATE INDEX chunks_content_fts_idx
ON chunks USING gin (to_tsvector('simple', COALESCE(content_normalized, content)));

-- 3. Update keyword search RPC to use normalized content for matching/ranking
CREATE OR REPLACE FUNCTION keyword_search_chunks(
    search_query text,
    match_count int DEFAULT 20,
    p_user_id uuid DEFAULT NULL,
    p_document_ids uuid[] DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    chunk_index int,
    content text,
    token_count int,
    metadata jsonb,
    created_at timestamptz,
    rank double precision,
    document_name text,
    filename text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        c.chunk_index,
        c.content,
        c.token_count,
        c.metadata,
        c.created_at,
        ts_rank(
            to_tsvector('simple', COALESCE(c.content_normalized, c.content)),
            plainto_tsquery('simple', search_query)
        )::double precision AS rank,
        d.filename AS document_name,
        d.filename
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.user_id = p_user_id
      AND d.status = 'ready'
      AND to_tsvector('simple', COALESCE(c.content_normalized, c.content)) @@ plainto_tsquery('simple', search_query)
      AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;

-- 8. Realtime (Ingest page live document status)
-- Filter on user_id requires FULL replica identity (not just PK).
ALTER TABLE documents REPLICA IDENTITY FULL;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE documents;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
