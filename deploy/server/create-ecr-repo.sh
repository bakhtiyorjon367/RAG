#!/usr/bin/env bash
# Create the rag-backend ECR repository (run with admin AWS credentials).
# Usage: ./deploy/server/create-ecr-repo.sh [AWS_REGION]
# Example: ./deploy/server/create-ecr-repo.sh us-east-1

set -euo pipefail

REGION="${1:-${AWS_REGION:-us-east-1}}"
REPO="rag-backend"

echo "Creating ECR repository '$REPO' in region '$REGION' (if missing)..."
aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1 && {
  echo "Repository already exists."
  aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" \
    --query 'repositories[0].repositoryUri' --output text
  exit 0
}

aws ecr create-repository \
  --repository-name "$REPO" \
  --region "$REGION" \
  --image-scanning-configuration scanOnPush=true

echo "Created. URI:"
aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" \
  --query 'repositories[0].repositoryUri' --output text
