# EC2 host setup (single box: backend container + frontend via nginx, HTTP)

One-time setup for the t3.medium (x86_64) instance that the
[deploy.yml](../../.github/workflows/deploy.yml) workflow targets.

Backend images are pushed to **GitHub Container Registry**:
`ghcr.io/<owner>/rag-backend` — no AWS ECR setup required.

## 1. Instance & security group

- Instance: t3.small/t3.medium (2–4 GB RAM). Default model is
  `multilingual-e5-base` (~1 GB baked in image, ~1 GB RAM at load).
- EBS volume: >= 20 GB (image ~2 GB + OS + Docker layers).
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

- First deploy: CI bakes the e5-base embedding model (~1 GB) into the Docker
  image. EC2 needs ~3 GB free for `docker pull` (~2 GB image). Run
  `docker system prune -af` if disk is above ~85% full before redeploying.
- If deploy failed with **No space left on device**, SSH in and free space, then
  re-run the workflow:

  ```bash
  docker stop rag-backend 2>/dev/null; docker rm rag-backend 2>/dev/null
  docker volume rm fastembed_cache 2>/dev/null
  docker system prune -af
  df -h /
  ```

  In AWS Console: EC2 → Volumes → modify root volume to **30 GB**, then on the
  instance: `sudo growpart /dev/nvme0n1 1 && sudo resize2fs /dev/nvme0n1p1`
  (device name may differ — check `lsblk`).
- Frontend is built with `VITE_API_URL=""` so it calls relative `/api/v1/...`,
  which nginx proxies to the backend.
- HTTP only for now. Add HTTPS later with certbot or an ALB.

See also [deploy/server/README.md](../server/README.md).
