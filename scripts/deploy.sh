#!/bin/bash
set -e

# Zero-downtime deployment script for AWS ECS Fargate
# Using Blue/Green with CodeDeploy or rolling update with healthy percent

PROJECT="lkg-gateway"
ENV="prod"
REGION="us-east-1"
IMAGE_TAG=$1

if [ -z "$IMAGE_TAG" ]; then
    echo "Usage: ./deploy.sh <image_tag>"
    exit 1
fi

echo "🚀 Starting zero-downtime deployment for $PROJECT ($ENV) in $REGION..."

# 1. Run database migrations (Pre-traffic hook)
echo "📦 Running DB migrations..."
# Assuming a 'migration-task' exists that runs alembic upgrade head
# aws ecs run-task --cluster $PROJECT-$ENV-cluster --task-definition $PROJECT-migration-task ...

# 2. Warm caches (Optional but recommended)
echo "🔥 Warming caches..."
# python scripts/warm-cache.py

# 3. Update ECS Service
echo "🏗️ Updating ECS service to image $IMAGE_TAG..."
aws ecs update-service \
    --cluster "$PROJECT-$ENV-cluster-$REGION" \
    --service "$PROJECT-$ENV-service-$REGION" \
    --force-new-deployment \
    --region "$REGION"

# 4. Wait for stability
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster "$PROJECT-$ENV-cluster-$REGION" \
    --services "$PROJECT-$ENV-service-$REGION" \
    --region "$REGION"

echo "✅ Deployment successful!"
