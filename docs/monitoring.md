# Monitoring and Logging System

This document describes the monitoring and logging system implemented for the FogisCalendarPhoneBookSync application.

## Overview

The application uses a comprehensive logging and monitoring system to track application performance, errors, and behavior. The system consists of:

1. **Structured Logging**: Using `structlog` for consistent, JSON-formatted logs with context preservation
2. **Metrics Collection**: Using Prometheus for collecting and storing metrics
3. **Visualization**: Using Grafana for visualizing metrics and creating dashboards
4. **Health Checks**: Enhanced health check endpoint with detailed system status

## Logging

### Configuration

Logging is configured in `logging_config.py` and provides:

- JSON-formatted logs for machine parsing
- Human-readable logs for development
- Log rotation to prevent disk space issues
- Consistent context across log entries

### Usage

To use the logging system in your code:

```python
from logger import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Log with context
logger.info("Operation started", user_id="123", operation="sync")

# Log errors with exception information
try:
    # Some operation
    pass
except Exception as e:
    logger.exception("Operation failed", error=str(e), operation="sync")
```

### Log Files

Logs are stored in the `logs` directory:

- `application.log`: Main log file
- `application.log.1`, `application.log.2`, etc.: Rotated log files

## Metrics

### Available Metrics

The application collects the following metrics:

- **API Request Latency**: Time taken to process API requests
- **Sync Operations**: Count of sync operations by result and type
- **Errors**: Count of errors by type
- **Active Syncs**: Gauge of currently active sync operations

### Prometheus

Prometheus is configured to scrape metrics from the application's `/metrics` endpoint. The configuration is in `prometheus/prometheus.yml`.

To access Prometheus:

1. Start the monitoring stack: `docker-compose -f docker-compose.monitoring.yml up -d`
2. Access Prometheus at `http://localhost:9090`

### Grafana

Grafana is configured with a dashboard for visualizing the application metrics. The dashboard is provisioned automatically when the monitoring stack starts.

To access Grafana:

1. Start the monitoring stack: `docker-compose -f docker-compose.monitoring.yml up -d`
2. Access Grafana at `http://localhost:3000`
3. Login with username `admin` and password `admin`
4. Navigate to the "FOGIS Sync Dashboard"

## Health Checks

The application provides a health check endpoint at `/health` that returns:

- Overall system status
- Status of individual components
- Key metrics
- Environment information

Example response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "data_directory": true,
    "token_file": true,
    "config_file": true
  },
  "metrics": {
    "uptime": 3600,
    "api_latency": 0.235,
    "error_rate": 0.01
  },
  "timestamp": "2023-05-15T14:30:45.123Z",
  "request_id": "f8d7e6c5-b4a3-42d1-9e8f-0123456789ab"
}
```

## Running the Monitoring Stack

To run the complete monitoring stack:

```bash
# Create necessary directories
mkdir -p prometheus grafana/provisioning/datasources grafana/dashboards logs

# Start the monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**: Check that the `logs` directory exists and is writable
2. **Metrics not showing in Grafana**: Check that Prometheus can reach the application at `fogis-sync:5003`
3. **Grafana dashboard not loading**: Check that the Prometheus data source is configured correctly

### Checking Log Files

To check the log files:

```bash
# View the latest logs
tail -f logs/application.log

# Search for errors
grep ERROR logs/application.log

# Count errors by type
grep ERROR logs/application.log | jq .error_type | sort | uniq -c
```

### Checking Prometheus Metrics

To check if metrics are being collected:

1. Access Prometheus at `http://localhost:9090`
2. Go to the "Status" > "Targets" page
3. Check that the `fogis-sync` target is "UP"
4. Try querying some metrics, e.g., `fogis_sync_total`
