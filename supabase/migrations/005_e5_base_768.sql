-- ============================================================
-- Switch embeddings: e5-large (1024) → e5-base (768)
-- ============================================================
-- Destroys all documents/chunks (incompatible vectors). Re-ingest after applying.
-- Run in Supabase SQL Editor after deploying the e5-base backend.

DROP FUNCTION IF EXISTS match_chunks(vector, int, uuid, uuid[]);
DROP FUNCTION IF EXISTS match_chunks(vector, integer, uuid, uuid[], float);

DROP INDEX IF EXISTS chunks_embedding_idx;

TRUNCATE chunks;
TRUNCATE documents CASCADE;

ALTER TABLE chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunks ADD COLUMN embedding vector(768);

CREATE INDEX chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(768),
    match_count int DEFAULT 10,
    p_user_id uuid DEFAULT NULL,
    p_document_ids uuid[] DEFAULT NULL,
    p_threshold float DEFAULT 0.5
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
