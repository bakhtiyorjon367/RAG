# AWS MVP deployment

Hybrid deployment: **static frontend + FastAPI on AWS**, **Supabase Cloud** for Postgres/auth/storage, **Gemini** for chat.

## Prerequisites

- AWS account with CLI configured (`aws configure`)
- Supabase project configured ([SUPABASE_SETUP.md](./SUPABASE_SETUP.md))
- Domain (optional) for HTTPS on ALB and CloudFront
- `./scripts/verify-supabase.sh` passes

## Architecture

| Layer | AWS service |
|-------|-------------|
| Frontend SPA | S3 + CloudFront, or Amplify Hosting |
| Backend API | ECS Fargate behind ALB, or App Runner |
| Secrets | AWS Secrets Manager or SSM Parameter Store |
| DB / Auth / Storage | Supabase Cloud (not on AWS for MVP) |

## Environment variables

### Backend (runtime — ECS / App Runner)

| Variable | Source |
|----------|--------|
| `SUPABASE_URL` | Supabase dashboard |
| `SUPABASE_ANON_KEY` | Supabase dashboard |
| `SUPABASE_SERVICE_KEY` | Secrets Manager |
| `GEMINI_API_KEY` | Secrets Manager |
| `CORS_ORIGINS` | `["https://your-cloudfront-domain.cloudfront.net"]` |
| `FASTEMBED_CACHE_PATH` | `/cache/fastembed` (mount EFS or ephemeral volume) |

### Frontend (build-time — Amplify / CodeBuild / docker build)

| Variable | Source |
|----------|--------|
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | Same as anon key |
| `VITE_API_URL` | Public API URL, e.g. `https://api.example.com` |

See [SUPABASE_PRODUCTION.md](./SUPABASE_PRODUCTION.md) for auth URL configuration.

---

## Option A — App Runner (simplest backend)

1. Create ECR repository and push the backend image:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=rag-backend

aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION 2>/dev/null || true

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -f backend/Dockerfile.prod -t $ECR_REPO:latest ./backend
docker tag $ECR_REPO:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
```

2. Store secrets in Secrets Manager (example names):

- `rag/supabase-service-key`
- `rag/gemini-api-key`

3. Create an App Runner service from the ECR image (Console or CLI):

- **Port:** 8000
- **Health check path:** `/health`
- **CPU / memory:** 2 vCPU, 4 GB (recommended for embedding model load)
- **Environment variables:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `CORS_ORIGINS`, `FASTEMBED_CACHE_PATH=/tmp/fastembed`
- **Secrets:** map Secrets Manager ARNs to `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`

Reference: [`deploy/aws/apprunner-service.json`](../deploy/aws/apprunner-service.json) (template).

---

## Option B — ECS Fargate + ALB

Use the templates under [`deploy/aws/`](../deploy/aws/):

1. `ecs-task-definition.json` — 4 GB task, port 8000, health check
2. `deploy-backend.sh` — build, push to ECR, register task definition

Steps:

```bash
cd deploy/aws
cp ecs-task-definition.json ecs-task-definition.local.json
# Edit: account ID, region, secret ARNs, Supabase URL, CORS_ORIGINS

./deploy-backend.sh
```

Then create (once, via Console or IaC):

- ECS cluster
- Fargate service with the task definition
- ALB target group → container port 8000, health check `/health`
- ACM certificate + HTTPS listener

---

## Frontend — Amplify Hosting

1. Connect the Git repository in **AWS Amplify**.
2. Use [`amplify.yml`](../amplify.yml) at the repo root.
3. Set environment variables in Amplify console (same `VITE_*` as above).
4. After deploy, copy the Amplify URL into Supabase auth Site URL and backend `CORS_ORIGINS`.

---

## Frontend — S3 + CloudFront

```bash
cd frontend
export VITE_SUPABASE_URL=https://<ref>.supabase.co
export VITE_SUPABASE_ANON_KEY=<anon-key>
export VITE_API_URL=https://<api-domain>
npm ci && npm run build

aws s3 sync dist/ s3://your-rag-frontend-bucket/ --delete
aws cloudfront create-invalidation --distribution-id EXXXXXXXXX --paths "/*"
```

Use [`deploy/aws/cloudfront-s3-notes.md`](../deploy/aws/cloudfront-s3-notes.md) for bucket policy and OAC setup.

---

## Local production smoke test

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up
# Frontend: http://localhost:8080  Backend: http://localhost:8000
```

---

## Post-deploy checklist

- [ ] `GET https://<api>/health` → `{"status":"ok"}`
- [ ] Sign up / sign in from production frontend URL
- [ ] Upload a PDF, run search and chat
- [ ] CloudWatch logs for ECS / App Runner show no OOM during startup
- [ ] Supabase production URLs configured ([SUPABASE_PRODUCTION.md](./SUPABASE_PRODUCTION.md))
