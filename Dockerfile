FROM python:3.9-slim

# Add build arguments for versioning
ARG VERSION=dev

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set version as environment variable
ENV VERSION=${VERSION}

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Create a directory for the fogis_api_client_python package
RUN mkdir -p /app/fogis_api_client_python

# We'll use a shell command directly instead of an entrypoint script

# Copy application code
COPY . .

# We'll install fogis_api_client at runtime via the entrypoint script

# Install other requirements
RUN pip install --no-cache-dir -r requirements.txt

# Try to install fogis_api_client from PyPI during build
RUN pip install --no-cache-dir fogis-api-client-timmyBird==0.0.5 || echo "Could not install fogis-api-client-timmyBird from PyPI"

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
