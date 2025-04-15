"""Metrics module for the application.

This module configures Prometheus metrics collection for the application.
It defines key metrics to track and provides functions to record metrics.
"""

from typing import Any, Dict, Optional

from flask import Flask
from prometheus_client import Counter, Gauge, Histogram
from prometheus_flask_exporter import PrometheusMetrics

# Initialize metrics (will be set by init_metrics)
# pylint: disable=invalid-name
_metrics = None

# Define custom metrics
# These are module-level variables that will be set by init_metrics
# pylint: disable=invalid-name
_SYNC_COUNTER = None
_API_LATENCY = None
_ERROR_COUNTER = None
_ACTIVE_SYNCS = None


def init_metrics(app: Flask) -> PrometheusMetrics:
    """Initialize Prometheus metrics for the application.

    Args:
        app: The Flask application to instrument

    Returns:
        The configured PrometheusMetrics instance
    """
    # pylint: disable=global-statement
    global _metrics, _SYNC_COUNTER, _API_LATENCY, _ERROR_COUNTER, _ACTIVE_SYNCS

    # Initialize with Flask app
    _metrics = PrometheusMetrics(app)

    # Define custom metrics
    _SYNC_COUNTER = Counter(
        "fogis_sync_total", "Total number of sync operations", ["result", "type"]
    )

    _API_LATENCY = Histogram(
        "fogis_api_request_latency_seconds", "API request latency", ["endpoint"]
    )

    _ERROR_COUNTER = Counter("fogis_error_total", "Total number of errors", ["type"])

    _ACTIVE_SYNCS = Gauge("fogis_active_syncs", "Number of active sync operations")

    # Add default metrics
    _metrics.info(
        "fogis_app_info",
        "Application information",
        version="1.0.0",
        app_name="FogisCalendarPhoneBookSync",
    )

    return _metrics


def track_sync(result: str, sync_type: str) -> None:
    """Track a sync operation.

    Args:
        result: The result of the sync operation (success, failure)
        sync_type: The type of sync operation (calendar, contacts)
    """
    if _SYNC_COUNTER:
        _SYNC_COUNTER.labels(result=result, type=sync_type).inc()


def track_api_latency(endpoint: str, seconds: float) -> None:
    """Track API request latency.

    Args:
        endpoint: The API endpoint being called
        seconds: The time taken in seconds
    """
    if _API_LATENCY:
        _API_LATENCY.labels(endpoint=endpoint).observe(seconds)


def track_error(error_type: str) -> None:
    """Track an error.

    Args:
        error_type: The type of error (api, auth, etc.)
    """
    if _ERROR_COUNTER:
        _ERROR_COUNTER.labels(type=error_type).inc()


class SyncOperation:
    """Context manager for tracking sync operations."""

    def __enter__(self):
        """Increment active syncs gauge when entering context."""
        if _ACTIVE_SYNCS:
            _ACTIVE_SYNCS.inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Decrement active syncs gauge when exiting context."""
        if _ACTIVE_SYNCS:
            _ACTIVE_SYNCS.dec()
