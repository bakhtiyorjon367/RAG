# EC2 host setup (single box: backend container + frontend via nginx, HTTP)

One-time setup for the t3.medium (x86_64) instance that the
[deploy.yml](../../.github/workflows/deploy.yml) workflow targets.

Backend images are pushed to **GitHub Container Registry**:
`ghcr.io/<owner>/rag-backend` — no AWS ECR setup required.

## 1. Instance & security group

- Instance: t3.medium minimum (4 GB RAM). The e5-large embedding model is
  memory-hungry on load; if you see OOM, move to t3.large or add swap.
- EBS volume: >= 20-30 GB (model cache ~2 GB + image ~1.5 GB + dist + OS).
- Security group inbound: open **80** (HTTP) and **22** (SSH) only.
  Do NOT expose 8000 — the backend binds to `127.0.0.1:8000` and is only
  reached through nginx.

## 2. Install Docker and nginx

Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y docker.io nginx
sudo systemctl enable --now docker
sudo systemctl enable --now nginx
sudo usermod -aG docker "$USER"   # re-login for group to take effect
```

## 3. Frontend directory

```bash
sudo mkdir -p /var/www/rag-frontend
sudo chown "$USER":"$USER" /var/www/rag-frontend
```

The frontend job copies `frontend/dist/*` here via scp.

## 4. nginx config

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
sudo cp ~/RAG/deploy/nginx/rag.conf /etc/nginx/conf.d/rag.conf
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t && sudo systemctl reload nginx
```

Or run `bash ~/RAG/deploy/server/setup-host.sh`.

## 5. GitHub repository secrets

| Secret | Notes |
|--------|-------|
| `EC2_HOST` / `EC2_USER` / `EC2_SSH_KEY` | SSH/scp target |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` | backend + frontend build |
| `GEMINI_API_KEY` | backend `/chat` |
| `GHCR_PAT` | Personal access token with **`read:packages`** — EC2 pulls from GHCR |

Push to GHCR uses the built-in **`GITHUB_TOKEN`** (no extra secret).

AWS credentials (`AWS_ACCOUNT_ID`, ECR policies, etc.) are **not** required
for this deploy path.

## Notes

- First deploy: CI creates the GHCR package on first push. The backend
  downloads the embedding model (~2 GB) into the `fastembed_cache` Docker
  volume before `/health` passes (workflow waits up to ~3 min).
- Frontend is built with `VITE_API_URL=""` so it calls relative `/api/v1/...`,
  which nginx proxies to the backend.
- HTTP only for now. Add HTTPS later with certbot or an ALB.

See also [deploy/server/README.md](../server/README.md).
