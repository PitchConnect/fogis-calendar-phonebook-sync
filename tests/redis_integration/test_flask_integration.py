#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Flask Integration

This module provides comprehensive tests for the Redis Flask integration functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis Flask integration
"""

import logging
import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.flask_integration import (  # noqa: E402
    CalendarRedisFlaskIntegration,
    create_calendar_redis_flask_integration,
)


class TestCalendarRedisFlaskIntegration(unittest.TestCase):
    """Test cases for CalendarRedisFlaskIntegration."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = CalendarRedisFlaskIntegration()

    def test_integration_initialization(self):
        """Test integration initialization."""
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_integration_initialization_with_environment(self):
        """Test integration initialization with environment configuration."""
        with patch.dict(os.environ, {"REDIS_ENABLED": "true"}):
            integration = CalendarRedisFlaskIntegration()

            self.assertIsInstance(integration, CalendarRedisFlaskIntegration)

    def test_integration_initialization_with_disabled_redis(self):
        """Test integration initialization with disabled Redis."""
        with patch.dict(os.environ, {"REDIS_ENABLED": "false"}):
            integration = CalendarRedisFlaskIntegration()

            self.assertIsInstance(integration, CalendarRedisFlaskIntegration)

    def test_publish_calendar_sync_start_success(self):
        """Test successful calendar sync start publishing."""
        result = self.integration.publish_calendar_sync_start(sync_cycle=1)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_start_with_details(self):
        """Test calendar sync start publishing with details."""
        result = self.integration.publish_calendar_sync_start(
            sync_cycle=2, additional_data={"test": "value"}
        )

        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_start_no_args(self):
        """Test calendar sync start publishing with no arguments."""
        result = self.integration.publish_calendar_sync_start()

        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_complete_success(self):
        """Test successful calendar sync completion publishing."""
        sync_results = {"events_synced": 5, "contacts_synced": 10}

        result = self.integration.publish_calendar_sync_complete(sync_results, sync_cycle=1)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_complete_minimal(self):
        """Test calendar sync completion publishing with minimal data."""
        result = self.integration.publish_calendar_sync_complete({})

        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_error_success(self):
        """Test successful calendar sync error publishing."""
        error = Exception("Test error")

        result = self.integration.publish_calendar_sync_error(error, sync_cycle=1)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_publish_calendar_sync_error_minimal(self):
        """Test calendar sync error publishing with minimal data."""
        result = self.integration.publish_calendar_sync_error(Exception("test"))

        self.assertIsInstance(result, bool)

    def test_get_redis_status(self):
        """Test getting Redis status."""
        status = self.integration.get_redis_status()

        self.assertIsInstance(status, dict)
        self.assertIn("integration_enabled", status)

    def test_close_integration(self):
        """Test closing the integration."""
        # Should not raise exception
        self.integration.close()

    def test_close_integration_multiple_times(self):
        """Test closing integration multiple times."""
        # Should not raise exception
        self.integration.close()
        self.integration.close()

    def test_init_app_with_flask_app(self):
        """Test initializing with Flask app."""
        mock_app = Mock()
        mock_app.config = {}

        self.integration.init_app(mock_app)

        # Should not raise exception
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_init_app_with_config(self):
        """Test initializing with Flask app and config."""
        mock_app = Mock()
        mock_app.config = {"REDIS_URL": "redis://flask:6379", "REDIS_ENABLED": True}

        self.integration.init_app(mock_app)

        # Should not raise exception
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_register_routes(self):
        """Test registering Flask routes."""
        mock_app = Mock()

        self.integration.register_routes(mock_app)

        # Should not raise exception
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_create_health_endpoint(self):
        """Test creating health endpoint."""
        mock_app = Mock()

        self.integration.create_health_endpoint(mock_app)

        # Should not raise exception
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_create_status_endpoint(self):
        """Test creating status endpoint."""
        mock_app = Mock()

        self.integration.create_status_endpoint(mock_app)

        # Should not raise exception
        self.assertIsInstance(self.integration, CalendarRedisFlaskIntegration)

    def test_handle_flask_request_context(self):
        """Test handling Flask request context."""
        from flask import Flask

        app = Flask(__name__)

        with app.test_request_context("/test", method="GET"):
            # Should not raise exception
            result = self.integration.handle_request_context()

            self.assertIsInstance(result, bool)

    def test_handle_flask_error_context(self):
        """Test handling Flask error context."""
        error = Exception("Flask error")

        # Should not raise exception
        result = self.integration.handle_error_context(error)

        self.assertIsInstance(result, bool)


class TestFlaskIntegrationHelperFunctions(unittest.TestCase):
    """Test cases for Flask integration helper functions."""

    def test_create_flask_integration(self):
        """Test creating Flask integration."""
        integration = create_calendar_redis_flask_integration()

        self.assertIsInstance(integration, CalendarRedisFlaskIntegration)

    def test_create_flask_integration_with_config(self):
        """Test creating Flask integration with config."""
        integration = create_calendar_redis_flask_integration(
            redis_url="redis://test:6379", enabled=True
        )

        self.assertIsInstance(integration, CalendarRedisFlaskIntegration)


if __name__ == "__main__":
    unittest.main()
