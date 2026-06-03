# S3 + CloudFront frontend deployment

## 1. S3 bucket

- Create bucket `rag-frontend-<account-id>` (or your naming convention)
- Block public access (recommended)
- Enable versioning (optional)

## 2. Build artifacts

From repo root:

```bash
cd frontend
export VITE_SUPABASE_URL=https://<ref>.supabase.co
export VITE_SUPABASE_ANON_KEY=<anon-key>
export VITE_API_URL=https://api.yourdomain.com
npm ci && npm run build
aws s3 sync dist/ s3://rag-frontend-<account-id>/ --delete
```

## 3. CloudFront

- Origin: S3 bucket (Origin Access Control — OAC)
- Default root object: `index.html`
- Custom error responses: **403** and **404** → `/index.html` with response code **200** (SPA routing)
- Viewer protocol: Redirect HTTP to HTTPS
- Alternate domain + ACM certificate (optional)

## 4. Backend CORS

Set on the API service:

```
CORS_ORIGINS=["https://d111111abcdef8.cloudfront.net"]
```

Use the exact CloudFront domain (or custom domain) with `https` and no trailing slash.

## 5. Supabase

Add the CloudFront URL to Site URL and Redirect URLs — see [docs/SUPABASE_PRODUCTION.md](../../docs/SUPABASE_PRODUCTION.md).
