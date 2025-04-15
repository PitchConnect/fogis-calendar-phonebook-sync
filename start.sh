#!/bin/bash
set -e

# Maximum number of retries
MAX_RETRIES=3
RETRY_DELAY=5

# Function to handle errors
handle_error() {
  echo "Error occurred. Cleaning up..."
  docker compose down
  exit 1
}

# Set trap for error handling
trap 'handle_error' ERR

# Pull images with retry logic
pull_with_retry() {
  local retries=0
  while [ $retries -lt $MAX_RETRIES ]; do
    if docker compose pull; then
      return 0
    else
      retries=$((retries+1))
      echo "Pull failed. Retry $retries of $MAX_RETRIES in $RETRY_DELAY seconds..."
      sleep $RETRY_DELAY
    fi
  done
  echo "Failed to pull images after $MAX_RETRIES attempts."
  return 1
}

# Build with retry logic
build_with_retry() {
  local retries=0
  while [ $retries -lt $MAX_RETRIES ]; do
    if docker compose build --no-cache; then
      return 0
    else
      retries=$((retries+1))
      echo "Build failed. Retry $retries of $MAX_RETRIES in $RETRY_DELAY seconds..."
      sleep $RETRY_DELAY
    fi
  done
  echo "Failed to build images after $MAX_RETRIES attempts."
  return 1
}

# Check if Docker daemon is running
if ! docker info > /dev/null 2>&1; then
  echo "Docker daemon is not running. Please start Docker first."
  exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
  echo "docker-compose.yml not found in current directory."
  exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
  echo "Warning: .env file not found. Creating empty .env file."
  touch .env
fi

# Try to pull images first
echo "Pulling images..."
pull_with_retry

# Build the services
echo "Building services..."
build_with_retry

# Start the services
echo "Starting services..."
docker compose up -d

# Check if services started successfully
if docker compose ps | grep -q "Exit"; then
  echo "Some services failed to start. Checking logs..."
  docker compose logs
  handle_error
else
  echo "All services started successfully!"
  echo "You can view logs with: docker compose logs -f"
fi
