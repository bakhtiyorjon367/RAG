# Supabase setup (local + production)

## 1. Create or restore a project

1. Open [Supabase Dashboard](https://supabase.com/dashboard).
2. Create a project or **Restore** a paused free-tier project.
3. Copy from **Settings → API**:
   - **Project URL** → `SUPABASE_URL` and `VITE_SUPABASE_URL`
   - **anon / publishable** key → `SUPABASE_ANON_KEY` and `VITE_SUPABASE_ANON_KEY`
   - **service_role / secret** key → `SUPABASE_SERVICE_KEY` (backend only, never commit)

Update the project root [`.env`](../.env) (copy from [`.env.example`](../.env.example)).

**Important:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY` must all come from the **same** Supabase project. If you create a new project, replace every key — leaving an old `SUPABASE_SERVICE_KEY` causes upload failures that look like CORS errors in the browser.

## 2. Apply database migrations

In **SQL Editor**, run in order:

1. [`supabase/migrations/001_init.sql`](../supabase/migrations/001_init.sql)
2. [`supabase/migrations/002_storage_documents_bucket.sql`](../supabase/migrations/002_storage_documents_bucket.sql)

If running `001_init.sql` fails with `column "user_id" does not exist`, an **old** `documents` table was already in the project: `CREATE TABLE IF NOT EXISTS` skipped creating the new shape. Re-run the updated `001_init.sql` (it now drops `chunks` + `documents` first), or run `DROP TABLE IF EXISTS chunks CASCADE; DROP TABLE IF EXISTS documents CASCADE;` manually then paste `001_init.sql` again. To **keep** existing rows, use [`003_add_documents_user_id.sql`](../supabase/migrations/003_add_documents_user_id.sql) instead of re-running `001`.

**Auth users vs backend keys:** Users created in the Supabase dashboard are normal `auth.users` rows. The backend does not store per-user secrets in `.env`; it uses `SUPABASE_SERVICE_KEY` plus the **JWT** the browser sends after login. Dashboard users must sign in through the app (set a password in Authentication → Users if needed).

## 3. Enable Email auth

**Authentication → Providers → Email** — enable sign-in and sign-up for the MVP login UI.

## 4. Verify connectivity

```bash
chmod +x scripts/verify-supabase.sh
./scripts/verify-supabase.sh
```

If you see `Could not resolve host` or connection errors:

- The project ref in the URL is wrong, or the project was deleted/paused.
- Restart the frontend after changing `VITE_*` vars: `cd frontend && npm run dev`.

## 5. Clear stale browser sessions

If the console shows repeated `refresh_token` errors after changing projects:

1. Safari/Chrome → DevTools → **Application** → **Local Storage** → `http://localhost:5173`
2. Delete keys starting with `sb-` (Supabase auth), or use a private window.
3. Reload and sign up / sign in again.

## 6. Production URLs

See [SUPABASE_PRODUCTION.md](./SUPABASE_PRODUCTION.md) for Site URL, redirect URLs, and CORS-related auth settings when deploying to AWS.
