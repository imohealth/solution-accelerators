#!/bin/bash
# Build and push Docker image to ECR for Ambient-AI-Solution

set -e

AWS_REGION="us-east-1"
REPO_NAME="imohealth/ci-alerts"
IMAGE_TAG="latest"
# repo is 664016696759.dkr.ecr.us-east-1.amazonaws.com/imohealth/ci-alerts
ACCOUNT_ID="664016696759"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"

echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION --profile SolutionEngineering-tooling | podman login --username AWS --password-stdin $ECR_URI

echo "Building Docker image..."
podman buildx build --platform linux/amd64 -t $REPO_NAME:$IMAGE_TAG .

echo "Tagging Docker image..."
podman tag $REPO_NAME:$IMAGE_TAG $ECR_URI:$IMAGE_TAG

echo "Pushing Docker image to ECR..."
podman push $ECR_URI:$IMAGE_TAG

echo "Done. Image pushed: $ECR_URI:$IMAGE_TAG"
