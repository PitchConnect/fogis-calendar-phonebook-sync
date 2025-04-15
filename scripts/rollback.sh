#!/bin/bash
set -e

# Rollback script for FogisCalendarPhoneBookSync
# This script rolls back to the previous version in case of deployment failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"

cd "$PROJECT_ROOT"

# Check if there's a backup to roll back to
if [ ! -L "$BACKUP_DIR/latest" ]; then
  echo "No backup found to roll back to!"
  exit 1
fi

LATEST_BACKUP=$(readlink "$BACKUP_DIR/latest")
echo "Rolling back to backup: $LATEST_BACKUP"

# Restore docker-compose files
cp "$LATEST_BACKUP/docker-compose.yml" "$PROJECT_ROOT/"
cp "$LATEST_BACKUP/docker-compose.prod.yml" "$PROJECT_ROOT/"
cp "$LATEST_BACKUP/docker-compose.dev.yml" "$PROJECT_ROOT/"

# Restore .env file
cp "$LATEST_BACKUP/.env" "$PROJECT_ROOT/"

# Restore token.json (if exists in backup)
if [ -f "$LATEST_BACKUP/token.json" ]; then
  echo "Restoring token.json..."
  cp "$LATEST_BACKUP/token.json" "$PROJECT_ROOT/"
fi

# Get previous version
PREVIOUS_VERSION=$(cat "$LATEST_BACKUP/version.txt")
export IMAGE_TAG=$PREVIOUS_VERSION

echo "Rolling back to version $PREVIOUS_VERSION"

# Restart with previous version
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify rollback
echo "Verifying rollback..."
sleep 5
MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s http://localhost:5003/health | grep -q "healthy"; then
    echo "Rollback successful! Service is healthy."
    exit 0
  fi

  echo "Service not ready yet, retrying in 5 seconds..."
  sleep 5
  RETRY_COUNT=$((RETRY_COUNT+1))
done

echo "Rollback failed! Service is not healthy after rollback."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs
exit 1
