#!/usr/bin/env bash
# Verify Supabase project URL is reachable and credentials work.
# Usage: ./scripts/verify-supabase.sh
# Loads SUPABASE_URL and SUPABASE_ANON_KEY from project root .env

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Missing ${ENV_FILE}. Copy .env.example to .env and fill in Supabase values."
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

if [[ -z "${SUPABASE_URL:-}" || "$SUPABASE_URL" == *"your-project"* || "$SUPABASE_URL" == "http://localhost:54321" ]]; then
  echo "WARN: SUPABASE_URL is unset or still a placeholder."
  echo "      Set it to https://<project-ref>.supabase.co from the Supabase dashboard."
fi

if [[ -z "${SUPABASE_ANON_KEY:-}" || "$SUPABASE_ANON_KEY" == "your-anon-key" ]]; then
  echo "ERROR: SUPABASE_ANON_KEY is unset or still a placeholder."
  exit 1
fi

echo "==> DNS / HTTP check: ${SUPABASE_URL}/auth/v1/health"
HEALTH_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
  "${SUPABASE_URL}/auth/v1/health" \
  -H "apikey: ${SUPABASE_ANON_KEY}" 2>/dev/null) || HEALTH_CODE="000"
echo "HTTP ${HEALTH_CODE}"
if [[ "$HEALTH_CODE" == "000" ]]; then
  echo ""
  echo "FAILED: Cannot resolve or connect to Supabase (DNS/network)."
  echo "  - Confirm the project is Active (not paused) in https://supabase.com/dashboard"
  echo "  - Verify SUPABASE_URL matches Settings → API → Project URL"
  echo "  - Clear browser localStorage for localhost:5173 if you changed projects"
  exit 1
fi

echo "==> Auth API (anon key)"
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
  "${SUPABASE_URL}/auth/v1/settings" \
  -H "apikey: ${SUPABASE_ANON_KEY}")
echo "GET /auth/v1/settings → HTTP ${HTTP_CODE}"
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "WARN: Unexpected status; check SUPABASE_ANON_KEY in dashboard."
fi

if [[ -n "${SUPABASE_SERVICE_KEY:-}" && "$SUPABASE_SERVICE_KEY" != "your-service-role-key" ]]; then
  echo "==> REST API (service role) — required for uploads"
  SERVICE_BODY=$(curl -sS -w "\n%{http_code}" \
    "${SUPABASE_URL}/rest/v1/documents?select=id&limit=1" \
    -H "apikey: ${SUPABASE_SERVICE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" 2>/dev/null) || SERVICE_BODY=$'\n000'
  SERVICE_CODE="${SERVICE_BODY##*$'\n'}"
  echo "GET /rest/v1/documents → HTTP ${SERVICE_CODE}"
  if [[ "$SERVICE_CODE" == "401" ]]; then
    echo ""
    echo "FAILED: SUPABASE_SERVICE_KEY is invalid for this project."
    echo "  - Open Supabase → Settings → API for project $(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+).*|\1|')"
    echo "  - Copy service_role / secret key into SUPABASE_SERVICE_KEY (not the anon key)"
    echo "  - All keys must be from the SAME project as SUPABASE_URL"
    exit 1
  fi
  if [[ "$SERVICE_CODE" == "404" ]]; then
    echo "WARN: 'documents' table missing — run supabase/migrations/001_init.sql"
  fi
fi

echo ""
echo "OK: Supabase endpoint is reachable."
echo "Next: run supabase/migrations/*.sql in SQL Editor if not done yet."
