#!/usr/bin/env bash
# Install RAG nginx site.
#
# Dedicated host (RAG owns :80) — default:
#   bash deploy/server/apply-nginx.sh deploy/nginx/rag.conf
#
# Shared host (another app on :80, RAG on :8080):
#   RAG_NGINX_COEXIST=1 bash deploy/server/apply-nginx.sh deploy/nginx/rag-port8080.conf
#
# Env:
#   RAG_NGINX_COEXIST=1  — do not disable other nginx vhosts; only add rag.conf
#   RAG_SMOKE_PORT=8080  — curl this port for smoke test (default: 80, or 8080 if set)

set -euo pipefail

RAG_CONF_SRC="${1:-/tmp/rag.conf}"
COEXIST="${RAG_NGINX_COEXIST:-0}"
SMOKE_PORT="${RAG_SMOKE_PORT:-}"

if [ ! -f "$RAG_CONF_SRC" ]; then
  echo "ERROR: nginx config not found: $RAG_CONF_SRC"
  exit 1
fi

if [ -z "$SMOKE_PORT" ]; then
  if grep -qE 'listen\s+8080' "$RAG_CONF_SRC" 2>/dev/null; then
    SMOKE_PORT=8080
  else
    SMOKE_PORT=80
  fi
fi

echo "==> Install $RAG_CONF_SRC -> /etc/nginx/conf.d/rag.conf"
sudo cp "$RAG_CONF_SRC" /etc/nginx/conf.d/rag.conf

if [ "$COEXIST" = "1" ]; then
  echo "==> Coexist mode: leaving other nginx sites unchanged"
else
  echo "==> Dedicated mode: disable other port-80 vhosts (RAG owns :80)"
  sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
  sudo rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

  shopt -s nullglob
  for f in /etc/nginx/sites-enabled/*; do
    echo "    disable $f"
    sudo mv "$f" "${f}.disabled.$(date +%s)" 2>/dev/null || sudo rm -f "$f"
  done

  for f in /etc/nginx/conf.d/*.conf; do
    [ "$(basename "$f")" = "rag.conf" ] && continue
    if grep -qE 'listen\s+80|listen\s+\[::\]:80' "$f" 2>/dev/null; then
      echo "    disable $f"
      sudo mv "$f" "${f}.disabled.$(date +%s)"
    fi
  done
fi

echo "==> Test and reload nginx"
sudo nginx -t
sudo systemctl reload nginx

echo "==> Smoke test (port $SMOKE_PORT)"
curl -fsSI "http://127.0.0.1:${SMOKE_PORT}/" | head -5
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null; then
  echo "WARNING: backend health on :8000 failed (container may still be starting)"
fi

PUBLIC_IP="$(curl -fsS --max-time 1 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<EC2_PUBLIC_IP>')"
echo "Done. Open http://${PUBLIC_IP}:${SMOKE_PORT}/"
