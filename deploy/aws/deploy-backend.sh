#!/usr/bin/env bash
# Build and push backend image to ECR, optionally register ECS task definition.
# Usage:
#   export AWS_REGION=us-east-1
#   ./deploy/aws/deploy-backend.sh
# Optional:
#   REGISTER_TASK=1 TASK_DEF=deploy/aws/ecs-task-definition.local.json ./deploy/aws/deploy-backend.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="${ECR_REPO:-rag-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

echo "==> Ensure ECR repository exists"
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" 2>/dev/null || \
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION"

echo "==> Docker login to ECR"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Build production image"
docker build -f "${ROOT}/backend/Dockerfile.prod" -t "${ECR_REPO}:${IMAGE_TAG}" "${ROOT}/backend"

docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"

echo "Pushed ${ECR_URI}:${IMAGE_TAG}"

if [[ "${REGISTER_TASK:-0}" == "1" ]]; then
  TASK_DEF="${TASK_DEF:-${ROOT}/deploy/aws/ecs-task-definition.json}"
  if [[ ! -f "$TASK_DEF" ]]; then
    echo "ERROR: Task definition not found: $TASK_DEF"
    exit 1
  fi
  echo "==> Register ECS task definition from ${TASK_DEF}"
  aws ecs register-task-definition --cli-input-json "file://${TASK_DEF}" --region "$AWS_REGION"
fi

echo "Done."
