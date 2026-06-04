#!/usr/bin/env bash
# One-time EC2 host setup for RAG (Ubuntu / Amazon Linux).
# Run after cloning the repo to ~/RAG:
#   git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
#   bash ~/RAG/deploy/server/setup-host.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_DIR="/var/www/rag-frontend"

echo "==> RAG host setup (repo root: $ROOT)"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not installed. Install docker first."
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "ERROR: nginx not installed. Install nginx first."
  exit 1
fi

echo "==> Frontend static directory: $FRONTEND_DIR"
sudo mkdir -p "$FRONTEND_DIR"
sudo chown -R "$USER":"$USER" "$FRONTEND_DIR"

echo "==> Install nginx site config"
bash "$ROOT/deploy/server/apply-nginx.sh" "$ROOT/deploy/nginx/rag.conf"
sudo systemctl enable nginx

echo "==> Ensure docker starts on boot"
sudo systemctl enable docker 2>/dev/null || true

echo ""
echo "Done. Next steps:"
echo "  1. Add GitHub secret GHCR_PAT (PAT with read:packages) for docker pull."
echo "  2. Re-run the Deploy workflow on GitHub."
echo "  3. Open http://<EC2_PUBLIC_IP>/ in a browser."
