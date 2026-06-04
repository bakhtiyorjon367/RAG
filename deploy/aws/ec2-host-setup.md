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

**Dedicated EC2 (only RAG on this machine):**

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
bash ~/RAG/deploy/server/apply-nginx.sh ~/RAG/deploy/nginx/rag.conf
```

**Shared EC2 (another app already on port 80, e.g. `root /var/www/html/dist`):**

Use a separate port for RAG so you do not replace the existing site:

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
RAG_NGINX_COEXIST=1 bash ~/RAG/deploy/server/apply-nginx.sh ~/RAG/deploy/nginx/rag-port8080.conf
```

- Open RAG at `http://<EC2_IP>:8080/`
- AWS security group: inbound **TCP 8080** (you already have this on `launch-wizard-2`)
- Supabase **Site URL** / **Redirect URLs**: use `http://<EC2_IP>:8080` (include the port)
- Backend `CORS_ORIGINS`: `["http://<EC2_IP>:8080"]` if you ever call the API cross-origin

Or run `bash ~/RAG/deploy/server/setup-host.sh` on a dedicated host only.

### Which port to pick when several are open?

Security group rules only allow traffic; they do not reserve a port. On the
instance, see what is actually listening:

```bash
sudo ss -tlnp | grep -E ':(80|443|3000|8080|9000|5678|30000|30001|30002)\s'
```

| Port | Typical use | RAG? |
|------|-------------|------|
| **80** | Your existing app (`/var/www/html/dist`) | No — leave for that app |
| **443** | HTTPS / reverse proxy | Only if you terminate TLS there |
| **8080** | Alt HTTP | **Yes — recommended for RAG** |
| 3000 | Dev UI (React, etc.) | Avoid unless you know it is free |
| 5678 | Often n8n | Avoid |
| 9000 | Often Portainer / MinIO console | Avoid |
| 30000–30002 | Custom / Node services | Avoid unless confirmed free |

Default CI settings (repo **Variables**, optional): `RAG_NGINX_PORT=8080`,
`RAG_NGINX_COEXIST=1`. Use `http://<EC2_IP>:8080/` in the browser and in
Supabase auth URLs.

## 5. GitHub repository secrets

| Secret                                                        | Notes                                                                |
| ------------------------------------------------------------- | -------------------------------------------------------------------- |
| `EC2_HOST` / `EC2_USER` / `EC2_SSH_KEY`                       | SSH/scp target                                                       |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` | backend + frontend build                                             |
| `GEMINI_API_KEY`                                              | backend `/chat`                                                      |
| `GHCR_PAT`                                                    | Personal access token with **`read:packages`** — EC2 pulls from GHCR |

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

## Troubleshooting: nginx `403 Forbidden` on `/`

`curl -I http://127.0.0.1/` returning **403** while `/var/www/rag-frontend/index.html`
exists means **another nginx vhost is still bound to port 80**, not `rag.conf`.

Common symptom — `nginx -T` shows the wrong document root:

```text
root /var/www/html/dist;    # stale / other app — NOT the RAG deploy path
```

instead of `root /var/www/rag-frontend;`.

On the EC2 host (clone repo once; `~/RAG` may be empty if you never cloned):

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git /tmp/RAG-install
bash /tmp/RAG-install/deploy/server/apply-nginx.sh /tmp/RAG-install/deploy/nginx/rag.conf

# Verify active config
sudo nginx -T 2>/dev/null | grep -E "listen 80|default_server|root "
curl -I http://127.0.0.1/    # expect HTTP/1.1 200
curl -fsS http://127.0.0.1:8000/health
```

To see which file defined the bad root before disabling it:

```bash
sudo grep -rn 'html/dist\|rag-frontend' /etc/nginx/
```

Re-run the GitHub **Deploy** workflow — the frontend job now copies `rag.conf` and
runs `apply-nginx.sh` on every deploy (no server-side git clone required).

## Troubleshooting: two different IPs / cross-origin frame errors

Use **one** URL for everything (e.g. `http://<EC2_PUBLIC_IP>/` only). Do not mix
an old IP, CloudFront URL, and EC2 in the same session.

In **Supabase → Authentication → URL configuration**, set **Site URL** and
**Redirect URLs** to the same origin you open in the browser, e.g.
`http://34.238.102.186` and `http://34.238.102.186/**`.

After changing frontend API behavior, redeploy so the build uses empty
`VITE_API_URL` (relative `/api/v1/...` via nginx).

See also [deploy/server/README.md](../server/README.md).
