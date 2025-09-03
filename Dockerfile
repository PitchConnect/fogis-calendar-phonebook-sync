# Optimized single-stage Docker build for improved performance
# Based on patterns from google-drive-service and team-logo-combiner
FROM python:3.11-slim-bookworm

# Build argument for version
ARG VERSION=dev
ENV VERSION=${VERSION}

# Install system dependencies with improved error handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security (following google-drive-service pattern)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy and install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 5003

# Health check with improved error handling (following google-drive-service pattern)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:5003/health || exit 1

# Use exec form for better signal handling
CMD ["python", "app.py"]
