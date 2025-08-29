# Multi-stage Docker build for optimized performance and caching
# Stage 1: Base image with system dependencies
FROM python:3.9-slim as base

# Add build arguments for versioning
ARG VERSION=dev

# Set environment variables early for better caching
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VERSION=${VERSION}

WORKDIR /app

# Install system dependencies in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Stage 2: Install Python dependencies with cache mounting
FROM base as dependencies

# Copy requirements files first to leverage Docker cache
COPY requirements.txt dev-requirements.txt ./

# Install Python dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Install fogis-api-client with specific version
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install fogis-api-client-timmyBird==0.5.1 || \
    echo "Could not install fogis-api-client-timmyBird from PyPI"

# Stage 3: Final application image
FROM base as final

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Create application directory structure
RUN mkdir -p /app/fogis_api_client_python

# Copy application code (excluding unnecessary files via .dockerignore)
COPY . .

# Expose the port the app runs on
EXPOSE 5003

# Use exec form for better signal handling
CMD ["python", "app.py"]
