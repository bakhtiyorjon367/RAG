#!/usr/bin/env bash
# Build frontend and sync to S3. Requires VITE_* env vars in shell or .env.
# Usage:
#   export S3_BUCKET=rag-frontend-123456789
#   export VITE_SUPABASE_URL=...
#   export VITE_SUPABASE_ANON_KEY=...
#   export VITE_API_URL=https://api.example.com
#   ./deploy/aws/deploy-frontend-s3.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
S3_BUCKET="${S3_BUCKET:?Set S3_BUCKET to your frontend bucket name}"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT}/.env"
  set +a
fi

: "${VITE_SUPABASE_URL:?Set VITE_SUPABASE_URL}"
: "${VITE_SUPABASE_ANON_KEY:?Set VITE_SUPABASE_ANON_KEY}"
: "${VITE_API_URL:?Set VITE_API_URL}"

echo "==> Build frontend"
cd "${ROOT}/frontend"
npm ci
npm run build

echo "==> Sync to s3://${S3_BUCKET}"
aws s3 sync dist/ "s3://${S3_BUCKET}/" --delete

if [[ -n "${CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
  echo "==> Invalidate CloudFront ${CLOUDFRONT_DISTRIBUTION_ID}"
  aws cloudfront create-invalidation \
    --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
    --paths "/*"
fi

echo "Done. Update CORS_ORIGINS and Supabase Site URL to match this frontend origin."
