-- ============================================================
-- Storage: documents bucket + RLS for user-scoped paths
-- Path pattern: {user_id}/{uuid}.ext (see backend ingestion)
-- Run in Supabase SQL Editor after 001_init.sql
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,
    52428800, -- 50 MB
    ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/html',
        'text/markdown',
        'text/x-markdown',
        'text/plain'
    ]::text[]
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Authenticated users: read/write/delete only under their own folder prefix
DROP POLICY IF EXISTS "documents_select_own_folder" ON storage.objects;
CREATE POLICY "documents_select_own_folder"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

DROP POLICY IF EXISTS "documents_insert_own_folder" ON storage.objects;
CREATE POLICY "documents_insert_own_folder"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

DROP POLICY IF EXISTS "documents_update_own_folder" ON storage.objects;
CREATE POLICY "documents_update_own_folder"
ON storage.objects FOR UPDATE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
)
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

DROP POLICY IF EXISTS "documents_delete_own_folder" ON storage.objects;
CREATE POLICY "documents_delete_own_folder"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);
