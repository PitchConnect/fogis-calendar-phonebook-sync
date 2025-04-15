"""Tests for the metrics module."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from prometheus_client import Counter, Gauge, Histogram
from prometheus_flask_exporter import PrometheusMetrics

import metrics

# pylint: disable=protected-access,redefined-outer-name


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    return app


def test_init_metrics_initializes_prometheus_metrics(app):
    """Test that init_metrics initializes PrometheusMetrics."""
    # Act
    result = metrics.init_metrics(app)

    # Assert
    assert isinstance(result, PrometheusMetrics)
    assert metrics._metrics is not None
    assert metrics._SYNC_COUNTER is not None
    assert metrics._API_LATENCY is not None
    assert metrics._ERROR_COUNTER is not None
    assert metrics._ACTIVE_SYNCS is not None


def test_track_sync_increments_counter():
    """Test that track_sync increments the sync counter."""
    # Arrange
    metrics._SYNC_COUNTER = MagicMock(spec=Counter)
    mock_labels = MagicMock()
    metrics._SYNC_COUNTER.labels.return_value = mock_labels

    # Act
    metrics.track_sync("success", "calendar")

    # Assert
    metrics._SYNC_COUNTER.labels.assert_called_once_with(result="success", type="calendar")
    mock_labels.inc.assert_called_once()


def test_track_api_latency_observes_histogram():
    """Test that track_api_latency observes the histogram."""
    # Arrange
    metrics._API_LATENCY = MagicMock(spec=Histogram)
    mock_labels = MagicMock()
    metrics._API_LATENCY.labels.return_value = mock_labels

    # Act
    metrics.track_api_latency("fogis", 1.23)

    # Assert
    metrics._API_LATENCY.labels.assert_called_once_with(endpoint="fogis")
    mock_labels.observe.assert_called_once_with(1.23)


def test_track_error_increments_counter():
    """Test that track_error increments the error counter."""
    # Arrange
    metrics._ERROR_COUNTER = MagicMock(spec=Counter)
    mock_labels = MagicMock()
    metrics._ERROR_COUNTER.labels.return_value = mock_labels

    # Act
    metrics.track_error("api")

    # Assert
    metrics._ERROR_COUNTER.labels.assert_called_once_with(type="api")
    mock_labels.inc.assert_called_once()


def test_sync_operation_context_manager():
    """Test that SyncOperation context manager increments and decrements the gauge."""
    # Arrange
    metrics._ACTIVE_SYNCS = MagicMock(spec=Gauge)

    # Act
    with metrics.SyncOperation():
        pass

    # Assert
    metrics._ACTIVE_SYNCS.inc.assert_called_once()
    metrics._ACTIVE_SYNCS.dec.assert_called_once()


def test_sync_operation_handles_exception():
    """Test that SyncOperation context manager decrements the gauge even if an exception occurs."""
    # Arrange
    metrics._ACTIVE_SYNCS = MagicMock(spec=Gauge)

    # Act
    try:
        with metrics.SyncOperation():
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Assert
    metrics._ACTIVE_SYNCS.inc.assert_called_once()
    metrics._ACTIVE_SYNCS.dec.assert_called_once()
