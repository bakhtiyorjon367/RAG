# Supabase production configuration

Configure these in the Supabase Dashboard when you have a live frontend URL (e.g. `https://app.example.com` from CloudFront or Amplify).

## Authentication → URL configuration

| Setting | Example |
|---------|---------|
| **Site URL** | `https://app.example.com` |
| **Redirect URLs** | `https://app.example.com/**`, `http://localhost:5173/**` (keep localhost for local dev) |

Email confirmation links and OAuth redirects use these values.

## Storage

Migrations create the private `documents` bucket and RLS policies for paths `{user_id}/...`.

The backend uploads with the **service role** key (bypasses RLS). Authenticated users can still access their folder via Storage policies if you add direct client downloads later.

Confirm in **Storage → documents** that the bucket exists after running `002_storage_documents_bucket.sql`.

## Realtime

The Ingest page subscribes to `documents` row updates. Ensure **Database → Replication** includes the `documents` table (enabled by default on new projects).

## Environment parity

Production frontend build must use the **same** Supabase project as the backend:

```
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
VITE_API_URL=https://api.example.com
```

Backend (ECS / App Runner):

```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_KEY=<service-role-key>
CORS_ORIGINS=["https://app.example.com"]
```

## Checklist before go-live

- [ ] Migrations `001` and `002` applied on production Supabase project
- [ ] Email auth enabled
- [ ] Site URL and redirect URLs include production domain
- [ ] `./scripts/verify-supabase.sh` passes against production `.env`
- [ ] `CORS_ORIGINS` on API matches frontend origin exactly (scheme + host, no trailing slash)
