#!/bin/bash
set -e

# Backup script for FogisCalendarPhoneBookSync
# This script creates a backup of the current deployment for potential rollback

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

cd "$PROJECT_ROOT"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f .env ]; then
  source .env
fi

# Get current version
CURRENT_VERSION=${VERSION:-unknown}

# Create backup metadata
echo "Creating backup of version $CURRENT_VERSION at $TIMESTAMP"
mkdir -p "$BACKUP_DIR/$TIMESTAMP"

# Backup docker-compose files
cp docker-compose.yml "$BACKUP_DIR/$TIMESTAMP/"
cp docker-compose.prod.yml "$BACKUP_DIR/$TIMESTAMP/"
cp docker-compose.dev.yml "$BACKUP_DIR/$TIMESTAMP/"

# Backup .env file
cp .env "$BACKUP_DIR/$TIMESTAMP/"

# Backup data directory (if needed)
if [ -d "data" ]; then
  echo "Backing up data directory..."
  cp -r data "$BACKUP_DIR/$TIMESTAMP/"
fi

# Backup token.json (if exists)
if [ -f "token.json" ]; then
  echo "Backing up token.json..."
  cp token.json "$BACKUP_DIR/$TIMESTAMP/"
fi

# Save current image tag
echo "$CURRENT_VERSION" > "$BACKUP_DIR/$TIMESTAMP/version.txt"

# Create a symlink to the latest backup
rm -f "$BACKUP_DIR/latest"
ln -s "$BACKUP_DIR/$TIMESTAMP" "$BACKUP_DIR/latest"

echo "Backup completed successfully to $BACKUP_DIR/$TIMESTAMP"
