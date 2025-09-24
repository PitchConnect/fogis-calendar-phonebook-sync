# flake8: noqa: E402#!/usr/bin/env python3
"""
Integration Tests for Calendar Service Redis Subscription

This module provides comprehensive integration tests for the Redis subscription functionality
in the FOGIS calendar service, testing end-to-end workflows.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Integration tests for calendar service Redis subscription
"""

import logging
import os

# Import modules to test
import sys
import threading
import time
import unittest
from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.config import RedisConfig
from redis_integration.flask_integration_simple import RedisFlaskIntegration
from redis_integration.subscriber_simple import RedisSubscriber

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRedisServiceIntegration(unittest.TestCase):
    """Integration test cases for Redis service."""

    def setUp(self):
        """Set up test fixtures."""
        self.calendar_sync_calls = []
        self.calendar_sync_results = []

        def mock_calendar_sync(matches):
            """Mock calendar sync function."""
            self.calendar_sync_calls.append(matches)
            if self.calendar_sync_results:
                return self.calendar_sync_results.pop(0)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    def test_redis_service_disabled(self):
        """Test Redis service when disabled."""
        service = CalendarServiceRedisService(
            enabled=False, calendar_sync_callback=self.mock_calendar_sync
        )

        self.assertFalse(service.enabled)
        self.assertIsNone(service.subscriber)

        # Operations should return appropriate responses
        self.assertFalse(service.start_redis_subscription())
        self.assertTrue(service.stop_redis_subscription())  # Should succeed (no-op)

        status = service.get_redis_status()
        self.assertFalse(status["enabled"])
        self.assertEqual(status["status"], "disabled")

    @patch("redis_integration.connection_manager.REDIS_AVAILABLE", False)
    def test_redis_service_without_redis_package(self):
        """Test Redis service when Redis package is not available."""
        service = CalendarServiceRedisService(
            enabled=True, calendar_sync_callback=self.mock_calendar_sync
        )

        self.assertTrue(service.enabled)
        self.assertIsNotNone(service.subscriber)

        # Should handle gracefully
        status = service.get_redis_status()
        self.assertTrue(status["enabled"])
        # Connection should fail but service should still be initialized

    @patch("redis_integration.connection_manager.redis")
    def test_redis_service_full_workflow(self, mock_redis):
        """Test complete Redis service workflow."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client

        service = CalendarServiceRedisService(
            redis_url="redis://test:6379",
            enabled=True,
            calendar_sync_callback=self.mock_calendar_sync,
        )

        # Mock successful subscription
        service.subscriber.connection_manager.subscribe_to_channel = Mock(return_value=True)
        service.subscriber.connection_manager.unsubscribe_from_channel = Mock(return_value=True)

        # Test starting subscription
        success = service.start_redis_subscription()
        self.assertTrue(success)

        # Test getting status
        status = service.get_redis_status()
        self.assertTrue(status["enabled"])
        self.assertIn("subscription_status", status)

        # Test manual sync
        test_matches = [{"matchid": 123456, "hemmalag": "Team A"}]
        sync_success = service.handle_manual_sync_request(test_matches)
        self.assertTrue(sync_success)
        self.assertEqual(len(self.calendar_sync_calls), 1)

        # Test stopping subscription
        stop_success = service.stop_redis_subscription()
        self.assertTrue(stop_success)

        # Test restart
        restart_success = service.restart_subscription()
        self.assertTrue(restart_success)

    def test_redis_service_callback_update(self):
        """Test updating calendar sync callback."""
        service = CalendarServiceRedisService(enabled=False)

        # Initially no callback
        self.assertIsNone(service.calendar_sync_callback)

        # Set callback
        service.set_calendar_sync_callback(self.mock_calendar_sync)
        self.assertEqual(service.calendar_sync_callback, self.mock_calendar_sync)

    def test_redis_service_statistics(self):
        """Test getting Redis service statistics."""
        service = CalendarServiceRedisService(
            enabled=False, calendar_sync_callback=self.mock_calendar_sync
        )

        stats = service.get_subscription_statistics()
        self.assertFalse(stats["enabled"])
        self.assertIn("statistics", stats)

    @patch("redis_integration.connection_manager.redis")
    def test_redis_service_testing(self, mock_redis):
        """Test Redis service testing functionality."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client

        service = CalendarServiceRedisService(
            enabled=True, calendar_sync_callback=self.mock_calendar_sync
        )

        # Mock successful operations
        service.subscriber.connection_manager.ensure_connection = Mock(return_value=True)
        service.subscriber.connection_manager.subscribe_to_channel = Mock(return_value=True)
        service.subscriber.connection_manager.unsubscribe_from_channel = Mock(return_value=True)

        test_results = service.test_redis_integration()

        self.assertTrue(test_results["enabled"])
        self.assertIn("test_results", test_results)


class TestFlaskIntegration(unittest.TestCase):
    """Integration test cases for Flask integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.calendar_sync_calls = []

        def mock_calendar_sync(matches):
            """Mock calendar sync function."""
            self.calendar_sync_calls.append(matches)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    def test_flask_integration_initialization(self):
        """Test Flask integration initialization."""
        from flask import Flask

        app = Flask(__name__)
        integration = CalendarRedisFlaskIntegration(app, self.mock_calendar_sync)

        self.assertIsNotNone(integration)
        self.assertEqual(integration.app, app)
        self.assertEqual(integration.calendar_sync_callback, self.mock_calendar_sync)
        self.assertIsNotNone(integration.redis_service)

        # Check that Redis service was added to app
        self.assertTrue(hasattr(app, "redis_service"))

    def test_flask_integration_deferred_initialization(self):
        """Test Flask integration with deferred initialization."""
        from flask import Flask

        integration = CalendarRedisFlaskIntegration()
        self.assertIsNone(integration.app)

        app = Flask(__name__)
        integration.init_app(app, self.mock_calendar_sync)

        self.assertEqual(integration.app, app)
        self.assertIsNotNone(integration.redis_service)

    @patch("redis_integration.connection_manager.REDIS_AVAILABLE", False)
    def test_flask_endpoints_redis_disabled(self):
        """Test Flask endpoints when Redis is disabled."""
        from flask import Flask

        app = Flask(__name__)
        integration = CalendarRedisFlaskIntegration(app, self.mock_calendar_sync)

        with app.test_client() as client:
            # Test Redis status endpoint
            response = client.get("/redis-status")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertFalse(data["redis_status"]["enabled"])

            # Test Redis config endpoint
            response = client.get("/redis-config")
            self.assertEqual(response.status_code, 200)

            # Test manual sync endpoint
            response = client.post("/manual-sync", json={"matches": [{"matchid": 123456}]})
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["matches_processed"], 1)

    def test_flask_manual_sync_invalid_data(self):
        """Test Flask manual sync endpoint with invalid data."""
        from flask import Flask

        app = Flask(__name__)
        integration = CalendarRedisFlaskIntegration(app, self.mock_calendar_sync)

        with app.test_client() as client:
            # Test with missing matches
            response = client.post("/manual-sync", json={})
            self.assertEqual(response.status_code, 400)

            data = response.get_json()
            self.assertFalse(data["success"])
            self.assertIn("Missing", data["error"])

            # Test with no JSON data
            response = client.post("/manual-sync")
            self.assertEqual(response.status_code, 400)

    def test_flask_callback_update(self):
        """Test updating callback through Flask integration."""
        from flask import Flask

        app = Flask(__name__)
        integration = CalendarRedisFlaskIntegration(app)

        # Initially no callback
        self.assertIsNone(integration.calendar_sync_callback)

        # Set callback
        integration.set_calendar_sync_callback(self.mock_calendar_sync)
        self.assertEqual(integration.calendar_sync_callback, self.mock_calendar_sync)


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end integration test cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.calendar_sync_calls = []
        self.calendar_sync_results = []

        def mock_calendar_sync(matches):
            """Mock calendar sync function."""
            self.calendar_sync_calls.append(matches)
            if self.calendar_sync_results:
                return self.calendar_sync_results.pop(0)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    @patch("redis_integration.connection_manager.redis")
    def test_complete_message_flow(self, mock_redis):
        """Test complete message flow from Redis to calendar sync."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client

        # Create service
        service = CalendarServiceRedisService(
            enabled=True, calendar_sync_callback=self.mock_calendar_sync
        )

        # Mock successful subscription
        service.subscriber.connection_manager.ensure_connection = Mock(return_value=True)
        service.subscriber.connection_manager.subscribe_to_channel = Mock(return_value=True)

        # Start subscription
        success = service.start_redis_subscription()
        self.assertTrue(success)

        # Simulate receiving a message
        test_message = {
            "message_id": "integration-test-123",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [
                    {"matchid": 123456, "hemmalag": "Team A", "bortalag": "Team B"},
                    {"matchid": 789012, "hemmalag": "Team C", "bortalag": "Team D"},
                ],
                "metadata": {
                    "has_changes": True,
                    "change_summary": {"new_matches": 2, "updated_matches": 0},
                },
            },
        }

        # Process message directly (simulating Redis message reception)
        service.subscriber._handle_redis_message(test_message)

        # Check that calendar sync was called
        self.assertEqual(len(self.calendar_sync_calls), 1)
        self.assertEqual(len(self.calendar_sync_calls[0]), 2)

        # Check statistics
        stats = service.get_subscription_statistics()
        self.assertTrue(stats["enabled"])
        self.assertEqual(stats["statistics"]["subscription_stats"]["total_messages_received"], 1)
        self.assertEqual(stats["statistics"]["subscription_stats"]["successful_messages"], 1)

    def test_configuration_integration(self):
        """Test configuration integration across components."""

        # Create custom configuration
        config = RedisSubscriptionConfig(
            url="redis://custom:6379",
            match_updates_channel="custom:matches",
            processor_status_channel="custom:status",
            system_alerts_channel="custom:alerts",
        )

        # Create subscriber with custom config
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=config, calendar_sync_callback=self.mock_calendar_sync
        )

        # Check that custom channels are used
        expected_channels = {
            "match_updates": "custom:matches",
            "processor_status": "custom:status",
            "system_alerts": "custom:alerts",
        }
        self.assertEqual(subscriber.channels, expected_channels)

    def test_error_handling_integration(self):
        """Test error handling across integration components."""

        # Create service with failing callback
        def failing_callback(matches):
            raise Exception("Calendar sync failed")

        service = CalendarServiceRedisService(
            enabled=False,  # Disabled to avoid Redis connection
            calendar_sync_callback=failing_callback,
        )

        # Test manual sync with failing callback
        test_matches = [{"matchid": 123456}]
        success = service.handle_manual_sync_request(test_matches)
        self.assertFalse(success)

        # Service should still be functional
        status = service.get_redis_status()
        self.assertFalse(status["enabled"])


if __name__ == "__main__":
    # Run integration tests
    unittest.main(verbosity=2)
