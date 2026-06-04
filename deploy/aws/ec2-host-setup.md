# EC2 host setup (single box: backend container + frontend via nginx, HTTP)

One-time setup for the t3.medium (x86_64) instance that the
[deploy.yml](../../.github/workflows/deploy.yml) workflow targets.

The workflow does NOT provision the host. Do the following once before the
first deploy.

## 1. Instance & security group

- Instance: t3.medium minimum (4 GB RAM). The e5-large embedding model is
  memory-hungry on load; if you see OOM, move to t3.large or add swap.
- EBS volume: >= 20-30 GB (model cache ~2 GB + image ~1.5 GB + dist + OS).
- Security group inbound: open **80** (HTTP) and **22** (SSH) only.
  Do NOT expose 8000 — the backend binds to `127.0.0.1:8000` and is only
  reached through nginx.

## 2. IAM (ECR pull from the host)

The deploy step runs `aws ecr get-login-password` on the EC2 host, so the
instance needs AWS credentials with ECR read access. Easiest: attach an
instance role with `AmazonEC2ContainerRegistryReadOnly`.

## 3. Install Docker, AWS CLI, nginx

Amazon Linux 2023:

```bash
sudo dnf update -y
sudo dnf install -y docker nginx awscli
sudo systemctl enable --now docker
sudo systemctl enable --now nginx
sudo usermod -aG docker "$USER"   # re-login for group to take effect
```

(Ubuntu: use `apt-get install -y docker.io nginx awscli` and the same
`systemctl` commands.)

## 4. Frontend directory

```bash
sudo mkdir -p /var/www/rag-frontend
sudo chown "$USER":"$USER" /var/www/rag-frontend
```

The frontend job copies `frontend/dist/*` here via scp.

## 5. nginx config

```bash
# from a checkout of the repo on the host, or copy the file over
sudo cp deploy/nginx/rag.conf /etc/nginx/conf.d/rag.conf
sudo rm -f /etc/nginx/conf.d/default.conf
sudo nginx -t && sudo systemctl reload nginx
```

## 6. ECR repository (AWS — not a folder on the server)

The backend image is pushed to **AWS ECR** repository `rag-backend`. This is
**not** the same as a directory on EC2.

**Option A — let GitHub Actions create it** (recommended): the workflow runs
`aws ecr create-repository` before the first push.

**Option B — create manually** from a machine with admin AWS credentials:

```bash
bash deploy/server/create-ecr-repo.sh "$AWS_REGION"
```

Or:

```bash
aws ecr create-repository --repository-name rag-backend --region "$AWS_REGION"
```

## 7. Optional: clone repo to `~/RAG` on the server

For nginx config and helper scripts on the host:

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
bash ~/RAG/deploy/server/setup-host.sh
```

See [deploy/server/README.md](../server/README.md).

## 8. GitHub repository secrets

Required by [deploy.yml](../../.github/workflows/deploy.yml):

| Secret | Notes |
|--------|-------|
| `AWS_ACCOUNT_ID` | e.g. 245115923256 — used to build the ECR registry URL |
| `AWS_REGION` | e.g. us-east-1 |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | CI user for building/pushing to ECR |
| `EC2_HOST` / `EC2_USER` / `EC2_SSH_KEY` | SSH/scp target |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` | backend + frontend build |
| `GEMINI_API_KEY` | backend `/chat` |

`CORS_ORIGINS` is not needed: nginx serves the UI and proxies `/api` on the
same origin, so requests are same-origin.

## Notes

- First deploy: the backend downloads the embedding model (~2 GB) into the
  `fastembed_cache` Docker volume before `/health` passes. The workflow waits
  up to ~3 min for this.
- The frontend is built with `VITE_API_URL=""` so it calls relative
  `/api/v1/...`, which nginx proxies to the backend.
- HTTP only for now. To add HTTPS later: point a domain at the EC2 IP and run
  certbot for nginx, or front the instance with an ALB.
