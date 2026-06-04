# EC2 server layout (`~/RAG`)

Use this folder on the EC2 host for **config and scripts**. It is **not** where
Docker images are stored.

## Important: two different "rag-backend" names

| Name | What it is | Where |
|------|------------|--------|
| **`rag-backend` (ECR repo)** | AWS container registry for Docker images | AWS ECR (cloud). Created automatically by CI or via `create-ecr-repo.sh`. |
| **`rag-backend` (container)** | Running FastAPI process | `docker ps` on EC2, listens on `127.0.0.1:8000`. |
| **`~/RAG`** | Optional checkout of this repo on the server | Your home directory — nginx config, setup scripts. |

Creating `~/RAG/rag-backend/` as a **folder on disk does not fix** the ECR
error. The registry repo must exist in **AWS ECR**.

## Recommended layout on EC2

After cloning the repo to `~/RAG`:

```
~/RAG/
  deploy/
    nginx/rag.conf      # copy to /etc/nginx/conf.d/
    server/
      setup-host.sh     # one-time host setup
      create-ecr-repo.sh
  ...
/var/www/rag-frontend/  # static UI (filled by GitHub Actions scp)
```

## One-time setup on the server

```bash
git clone https://github.com/bakhtiyorjon367/RAG.git ~/RAG
cd ~/RAG
bash deploy/server/setup-host.sh
```

Then in the **AWS Console** (admin user, not the EC2 instance role):

- IAM → Users → `githubActions` → attach `AmazonEC2ContainerRegistryPowerUser`
- IAM → Roles → `instanceRole` → attach `AmazonEC2ContainerRegistryReadOnly`

Create the ECR repo once (or let the next GitHub Actions run create it):

```bash
bash ~/RAG/deploy/server/create-ecr-repo.sh us-east-1
```

Replace `us-east-1` with your `AWS_REGION` secret value.
