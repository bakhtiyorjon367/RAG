-- Enable Realtime on documents (run if Ingest live updates don't work)
-- Dashboard alternative: Database → Replication → supabase_realtime → enable "documents"

ALTER TABLE documents REPLICA IDENTITY FULL;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE documents;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
