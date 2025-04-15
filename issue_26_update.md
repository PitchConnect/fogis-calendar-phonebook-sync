# Implement Error Monitoring and Logging System

## Description

The application currently has basic logging but would benefit from a more robust monitoring and logging system. This issue outlines the implementation of a comprehensive logging and monitoring solution.

## Technical Specifications

### 1. Structured Logging Implementation

**Recommended Libraries:**
- **Primary: [structlog](https://www.structlog.org/en/stable/)** - Provides structured logging with context preservation
- **Alternative: [loguru](https://github.com/Delgan/loguru)** - Simpler API but less flexible for structured data

**Log Format:**
```json
{
  "timestamp": "2023-05-15T14:30:45.123Z",
  "level": "INFO",
  "logger": "fogis_sync.calendar",
  "message": "Calendar event created",
  "request_id": "f8d7e6c5-b4a3-42d1-9e8f-0123456789ab",
  "user_id": "user@example.com",
  "event_id": "evt_12345",
  "match_id": "match_67890",
  "elapsed_ms": 235,
  "environment": "production"
}
```

**Standard Context Fields:**
- `request_id`: Unique ID for tracking requests across services
- `user_id`: User identifier (when authenticated)
- `environment`: Deployment environment (dev/prod)
- `version`: Application version
- `elapsed_ms`: Execution time for performance tracking

**Log Levels and Usage:**
- `DEBUG`: Detailed information, only valuable for debugging
- `INFO`: Confirmation that things are working as expected
- `WARNING`: Indication that something unexpected happened, but the application still works
- `ERROR`: Due to a more serious problem, the application couldn't perform some function
- `CRITICAL`: A serious error indicating the application may be unable to continue running

### 2. Log Management

**Log Rotation:**
- Use [Python-Rotating-FileHandler](https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler) for local log rotation
- Configure Docker to use [logging drivers](https://docs.docker.com/config/containers/logging/configure/) for containerized logs
- Rotate logs based on size (10MB) and time (daily)
- Keep 30 days of logs by default

**Storage Configuration:**
```python
# Example configuration
{
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.processors.JSONRenderer()"
        }
    },
    "handlers": {
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/application.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 30,
            "formatter": "json"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "loggers": {
        "": {
            "handlers": ["rotating_file", "console"],
            "level": "INFO"
        }
    }
}
```

### 3. Monitoring Integration

**Recommended Solutions:**
- **Primary: [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/)** - Industry standard for metrics collection and visualization
- **Alternative: [ELK Stack](https://www.elastic.co/elastic-stack)** - Better for log analysis but more resource-intensive

**Key Metrics to Monitor:**
- Request rate and latency
- Error rate (by endpoint and error type)
- Sync success/failure rate
- External API call latency (FOGIS, Google)
- Resource usage (CPU, memory, disk)

**Alert Configuration:**
- Set up alerts for:
  - Error rate exceeding threshold (e.g., >5% of requests)
  - API latency above threshold (e.g., >2s)
  - Failed syncs
  - Resource constraints (e.g., disk space <10%)

**Dashboard Example:**
![Example Grafana Dashboard](https://grafana.com/api/dashboards/1860/images/1718/image)

### 4. Performance Metrics Collection

**Recommended Libraries:**
- **[Prometheus Client](https://github.com/prometheus/client_python)** for metrics collection
- **[Flask-Prometheus](https://github.com/rycus86/prometheus_flask_exporter)** for Flask integration

**Key Metrics to Collect:**
- **Counters:** API calls, sync operations, errors
- **Gauges:** Active users, queue size
- **Histograms:** Request duration, API latency
- **Summaries:** Request size, response size

**Example Implementation:**
```python
from prometheus_client import Counter, Histogram
from prometheus_flask_exporter import PrometheusMetrics

# Initialize with Flask app
metrics = PrometheusMetrics(app)

# Define custom metrics
sync_counter = Counter('fogis_sync_total', 'Total number of sync operations',
                      ['result', 'type'])
api_latency = Histogram('fogis_api_request_latency_seconds',
                        'FOGIS API request latency',
                        ['endpoint'])

# Usage in code
def sync_calendar():
    with api_latency.labels(endpoint='calendar').time():
        # Perform sync
        if success:
            sync_counter.labels(result='success', type='calendar').inc()
        else:
            sync_counter.labels(result='failure', type='calendar').inc()
```

## Implementation Steps

### 1. Set Up Structured Logging

1. Install required packages:
   ```bash
   pip install structlog python-json-logger
   ```

2. Create a logging configuration module (`logging_config.py`):
   ```python
   import logging
   import sys
   import time
   from typing import Dict, Any

   import structlog

   def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
       """Configure structured logging."""
       # Processors for structlog
       processors = [
           structlog.stdlib.add_log_level,
           structlog.stdlib.add_logger_name,
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.UnicodeDecoder(),
       ]

       # Add JSON renderer if requested
       if json_format:
           processors.append(structlog.processors.JSONRenderer())
       else:
           processors.append(structlog.dev.ConsoleRenderer())

       # Configure structlog
       structlog.configure(
           processors=processors,
           context_class=dict,
           logger_factory=structlog.stdlib.LoggerFactory(),
           wrapper_class=structlog.stdlib.BoundLogger,
           cache_logger_on_first_use=True,
       )

       # Configure standard logging
       logging.basicConfig(
           format="%(message)s",
           stream=sys.stdout,
           level=getattr(logging, log_level),
       )
   ```

3. Create a logger factory (`logger.py`):
   ```python
   import structlog
   from typing import Dict, Any

   def get_logger(name: str) -> structlog.BoundLogger:
       """Get a structured logger with the given name."""
       return structlog.get_logger(name)
   ```

4. Initialize logging in `app.py`:
   ```python
   from logging_config import configure_logging

   # Configure logging early in application startup
   configure_logging(log_level="INFO", json_format=True)
   ```

5. Use the logger throughout the application:
   ```python
   from logger import get_logger

   logger = get_logger(__name__)

   def sync_calendar(match_id):
       logger.info("Starting calendar sync", match_id=match_id)
       try:
           # Sync logic
           logger.info("Calendar sync completed", match_id=match_id, status="success")
       except Exception as e:
           logger.exception("Calendar sync failed", match_id=match_id, error=str(e))
           raise
   ```

### 2. Implement Log Rotation

1. Update Docker Compose configuration:
   ```yaml
   services:
     fogis-sync:
       # ... existing config
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "30"
   ```

2. Create log directory in Dockerfile:
   ```dockerfile
   # ... existing Dockerfile

   # Create log directory
   RUN mkdir -p /app/logs && chmod 777 /app/logs

   # ... rest of Dockerfile
   ```

3. Update logging configuration to use rotating file handler:
   ```python
   # In logging_config.py

   import logging.handlers

   # ... existing code

   # Add file handler
   file_handler = logging.handlers.RotatingFileHandler(
       filename="logs/application.log",
       maxBytes=10 * 1024 * 1024,  # 10MB
       backupCount=30,
   )
   file_handler.setFormatter(logging.Formatter("%(message)s"))
   logging.getLogger().addHandler(file_handler)
   ```

### 3. Set Up Prometheus and Grafana

1. Add Prometheus and Grafana to Docker Compose:
   ```yaml
   services:
     # ... existing services

     prometheus:
       image: prom/prometheus
       volumes:
         - ./prometheus:/etc/prometheus
         - prometheus_data:/prometheus
       ports:
         - "9090:9090"
       restart: unless-stopped

     grafana:
       image: grafana/grafana
       volumes:
         - grafana_data:/var/lib/grafana
       ports:
         - "3000:3000"
       restart: unless-stopped
       depends_on:
         - prometheus

   volumes:
     prometheus_data:
     grafana_data:
   ```

2. Create Prometheus configuration:
   ```yaml
   # ./prometheus/prometheus.yml
   global:
     scrape_interval: 15s

   scrape_configs:
     - job_name: 'fogis-sync'
       static_configs:
         - targets: ['fogis-sync:5003']
   ```

3. Integrate Prometheus with Flask:
   ```python
   # In app.py
   from prometheus_flask_exporter import PrometheusMetrics

   # ... existing code

   # Initialize Prometheus metrics
   metrics = PrometheusMetrics(app)

   # Track request latency by endpoint
   metrics.info('app_info', 'Application info', version='1.0.0')
   ```

4. Add custom metrics for sync operations:
   ```python
   # In fogis_calendar_sync.py
   from prometheus_client import Counter, Histogram, Gauge

   # Define metrics
   SYNC_COUNTER = Counter('fogis_sync_total', 'Total sync operations', ['result', 'type'])
   SYNC_DURATION = Histogram('fogis_sync_duration_seconds', 'Sync duration in seconds', ['type'])
   MATCH_GAUGE = Gauge('fogis_matches_total', 'Total number of matches')

   # Use in sync function
   def sync_calendar():
       with SYNC_DURATION.labels(type='calendar').time():
           try:
               # Sync logic
               MATCH_GAUGE.set(len(matches))
               SYNC_COUNTER.labels(result='success', type='calendar').inc()
           except Exception:
               SYNC_COUNTER.labels(result='failure', type='calendar').inc()
               raise
   ```

### 4. Set Up Health Check Endpoint

1. Enhance the existing health check endpoint:
   ```python
   @app.route("/health", methods=["GET"])
   def health_check():
       """Enhanced health check endpoint with metrics."""
       try:
           # Basic checks
           checks = {
               "data_directory": os.path.exists("data"),
               "token_file": os.path.exists("token.json"),
               "google_api": check_google_api_connection(),
               "fogis_api": check_fogis_api_connection()
           }

           # Determine overall status
           status = "healthy" if all(checks.values()) else "unhealthy"

           # Get metrics
           metrics = {
               "sync_success_rate": calculate_sync_success_rate(),
               "api_latency": get_average_api_latency(),
               "error_rate": get_error_rate()
           }

           return jsonify({
               "status": status,
               "version": get_version(),
               "environment": os.environ.get("ENVIRONMENT", "development"),
               "checks": checks,
               "metrics": metrics,
               "timestamp": datetime.datetime.utcnow().isoformat()
           }), 200 if status == "healthy" else 503
       except Exception as e:
           logger.exception("Health check failed")
           return jsonify({"status": "error", "message": str(e)}), 500
   ```

## Testing the Implementation

1. **Unit Tests:**
   - Test structured logging format
   - Test log rotation
   - Test metrics collection

2. **Integration Tests:**
   - Test Prometheus endpoint
   - Test health check endpoint
   - Test log aggregation

3. **Manual Verification:**
   - Check Grafana dashboards
   - Verify log files are rotating correctly
   - Test alerts by triggering error conditions

## Documentation

1. Update project documentation with:
   - Logging standards and practices
   - Monitoring setup instructions
   - Dashboard access and usage
   - Alert configuration

2. Add comments to code explaining logging context and metrics

## Acceptance Criteria

- [ ] Structured logs are generated in a consistent JSON format
- [ ] Log rotation is configured and working properly
- [ ] Prometheus and Grafana are set up and collecting metrics
- [ ] Dashboard shows key application metrics:
  - Request rate and latency
  - Error rate
  - Sync success/failure rate
  - Resource usage
- [ ] Health check endpoint provides comprehensive status information
- [ ] Documentation is updated with logging and monitoring details
- [ ] Tests verify logging and monitoring functionality

## Resources

- [structlog Documentation](https://www.structlog.org/en/stable/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
- [ELK Stack Documentation](https://www.elastic.co/guide/index.html)
- [Docker Logging Best Practices](https://docs.docker.com/config/containers/logging/configure/)
