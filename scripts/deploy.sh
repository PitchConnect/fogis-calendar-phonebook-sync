#!/bin/bash
set -e

# Deployment script for FogisCalendarPhoneBookSync
# This script is used by GitHub Actions to deploy the application

# Usage: ./deploy.sh [environment]
# environment: 'development' or 'production' (default: development)

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Set image tag from environment or use latest
IMAGE_TAG=${VERSION:-latest}
export IMAGE_TAG

echo "Deploying version $IMAGE_TAG to $ENVIRONMENT environment"

# Pull the latest image
echo "Pulling latest image..."
docker pull ghcr.io/${GITHUB_REPOSITORY:-fogiscalendarphonebooksync}:$IMAGE_TAG

# Deploy with the appropriate docker-compose file
if [ "$ENVIRONMENT" = "production" ]; then
  echo "Deploying to production environment..."
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
else
  echo "Deploying to development environment..."
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
fi

# Verify deployment
echo "Verifying deployment..."
sleep 5
MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s http://localhost:5003/health | grep -q "healthy"; then
    echo "Service is healthy!"
    exit 0
  fi

  echo "Service not ready yet, retrying in 5 seconds..."
  sleep 5
  RETRY_COUNT=$((RETRY_COUNT+1))
done

echo "Service failed to start properly after 60 seconds"
if [ "$ENVIRONMENT" = "production" ]; then
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs
  echo "Rolling back to previous version..."
  "$SCRIPT_DIR/rollback.sh"
else
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs
fi

exit 1
