# EC2 server layout (`~/RAG`)

Use this folder on the EC2 host for **config and scripts**. Docker images are
stored in **GitHub Container Registry (GHCR)**, not on disk under `~/RAG`.

## Image location

| Name | What it is | Where |
|------|------------|--------|
| **`ghcr.io/bakhtiyorjon367/rag-backend`** | Backend Docker image | GitHub Container Registry (created on first CI push) |
| **`rag-backend` (container)** | Running FastAPI process | `docker ps` on EC2, listens on `127.0.0.1:8000` |
| **`~/RAG`** | Optional repo clone on the server | nginx config, setup scripts |

## Recommended layout on EC2

```
~/RAG/
  deploy/
    nginx/rag.conf      # copy to /etc/nginx/conf.d/
    server/
      setup-host.sh     # one-time host setup
  ...
/var/www/rag-frontend/  # static UI (filled by GitHub Actions scp)
```

## One-time setup on the server

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
bash ~/RAG/deploy/server/setup-host.sh
```

## GitHub repository variables (optional)

| Variable | Default in CI | Meaning |
|----------|---------------|---------|
| `RAG_NGINX_PORT` | `8080` | Public nginx port for the RAG UI (`80` on a dedicated host) |
| `RAG_NGINX_COEXIST` | `1` | `1` = do not disable other nginx sites; `0` = RAG owns port 80 |

Set **Variables** (not secrets) under repo Settings → Secrets and variables → Actions.

## GitHub secrets for GHCR pull on EC2

CI pushes with `GITHUB_TOKEN` (automatic). The EC2 host must **pull** the
image, so add a Personal Access Token:

1. GitHub → Settings → Developer settings → Personal access tokens
2. Create a token with **`read:packages`** scope
3. Add it as repository secret **`GHCR_PAT`**

If the package is **public** (Package settings → Change visibility), you can
skip `GHCR_PAT` and remove the `docker login` line from the workflow — but
private is recommended.

## No AWS ECR required

This project no longer uses AWS ECR. You do **not** need `AWS_ACCOUNT_ID`,
`AWS_ACCESS_KEY_ID`, or ECR IAM policies for deploy.
