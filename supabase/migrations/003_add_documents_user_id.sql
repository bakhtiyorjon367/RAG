-- ============================================================
-- Upgrade: add documents.user_id when table predates 001_init.sql
--
-- Error this fixes:
--   column documents.user_id does not exist (42703)
--
-- Run in Supabase SQL Editor AFTER checking your schema.
-- Dashboard Auth users do NOT need separate backend keys; this only
-- fixes the table shape and links rows to auth.users(id).
-- ============================================================

-- 1. Add column (nullable until backfill)
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Backfill orphan rows (pick ONE approach, then uncomment):

-- A) Dev: attach all existing documents to the oldest Auth user
-- UPDATE documents
-- SET user_id = (SELECT id FROM auth.users ORDER BY created_at ASC LIMIT 1)
-- WHERE user_id IS NULL;

-- B) Production: set your dashboard user's UUID from Authentication → Users
-- UPDATE documents
-- SET user_id = '00000000-0000-0000-0000-000000000000'::uuid
-- WHERE user_id IS NULL;

-- 3. After every row has user_id, enforce NOT NULL
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM documents WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'Backfill required: some documents still have NULL user_id. Run step 2 in this file.';
  END IF;
  ALTER TABLE documents ALTER COLUMN user_id SET NOT NULL;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- 4. Per-user dedup constraint (drop global hash unique if present)
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_content_hash_key;
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_content_hash_unique;
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_user_content_hash_unique;
ALTER TABLE documents
  ADD CONSTRAINT documents_user_content_hash_unique UNIQUE (user_id, content_hash);

CREATE INDEX IF NOT EXISTS documents_user_id_idx ON documents(user_id);

-- 5. RLS policies (idempotent)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
CREATE POLICY "Users can view their own documents" ON documents
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
CREATE POLICY "Users can insert their own documents" ON documents
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
CREATE POLICY "Users can update their own documents" ON documents
  FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;
CREATE POLICY "Users can delete their own documents" ON documents
  FOR DELETE USING (auth.uid() = user_id);

-- 6. Realtime (Ingest page live updates)
ALTER PUBLICATION supabase_realtime ADD TABLE documents;
