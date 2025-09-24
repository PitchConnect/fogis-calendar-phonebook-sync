#!/usr/bin/env python3
"""
Tests for Redis Integration

Comprehensive test suite for Redis pub/sub integration functionality.
"""

import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path for imports (must be before local imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Local imports after path modification
from redis_integration import (  # noqa: E402
    RedisConfig,
    RedisFlaskIntegration,
    RedisSubscriber,
)


class TestRedisConfig(unittest.TestCase):
    """Test Redis configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RedisConfig()

        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertTrue(config.enabled)
        self.assertEqual(config.timeout, 5)
        self.assertIsNotNone(config.channels)
        self.assertEqual(len(config.channels), 3)

    @patch.dict(
        os.environ,
        {"REDIS_URL": "redis://test:6379", "REDIS_ENABLED": "false", "REDIS_TIMEOUT": "10"},
    )
    def test_config_from_environment(self):
        """Test configuration loading from environment."""
        config = RedisConfig.from_environment()

        self.assertEqual(config.url, "redis://test:6379")
        self.assertFalse(config.enabled)
        self.assertEqual(config.timeout, 10)


class TestRedisSubscriber(unittest.TestCase):
    """Test Redis subscriber functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RedisConfig(url="redis://test:6379", enabled=True)
        self.calendar_sync_calls = []

        def mock_calendar_sync(matches):
            self.calendar_sync_calls.append(matches)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    def test_subscriber_initialization(self):
        """Test subscriber initialization."""
        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        self.assertEqual(subscriber.config, self.config)
        self.assertEqual(subscriber.calendar_sync_callback, self.mock_calendar_sync)
        self.assertFalse(subscriber.running)

    def test_subscriber_disabled(self):
        """Test subscriber when Redis is disabled."""
        config = RedisConfig(enabled=False)
        subscriber = RedisSubscriber(config, self.mock_calendar_sync)

        # Should not attempt to connect
        self.assertIsNone(subscriber.client)

        # Start subscription should return False
        result = subscriber.start_subscription()
        self.assertFalse(result)

    @patch("redis_integration.subscriber.redis")
    def test_subscriber_connection(self, mock_redis):
        """Test Redis connection."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        # Should have connected
        self.assertIsNotNone(subscriber.client)
        mock_redis.from_url.assert_called_once()

    def test_message_handling(self):
        """Test message handling."""
        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        # Test match update message
        test_message = {
            "type": "match_updates",
            "payload": {"matches": [{"matchid": 123456}], "metadata": {"has_changes": True}},
        }

        subscriber._handle_match_updates(test_message)

        # Should have called calendar sync
        self.assertEqual(len(self.calendar_sync_calls), 1)
        self.assertEqual(self.calendar_sync_calls[0], [{"matchid": 123456}])

    def test_status(self):
        """Test status reporting."""
        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        status = subscriber.get_status()

        self.assertIn("enabled", status)
        self.assertIn("connected", status)
        self.assertIn("subscribed", status)
        self.assertIn("redis_available", status)


class TestFlaskIntegration(unittest.TestCase):
    """Test Flask integration."""

    def setUp(self):
        """Set up test fixtures."""
        from flask import Flask

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

        self.calendar_sync_calls = []

        def mock_calendar_sync(matches):
            self.calendar_sync_calls.append(matches)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    @patch("redis_integration.flask_integration.create_redis_subscriber")
    def test_flask_integration_init(self, mock_create_subscriber):
        """Test Flask integration initialization."""
        mock_subscriber = Mock()
        mock_subscriber.start_subscription.return_value = True
        mock_create_subscriber.return_value = mock_subscriber

        integration = RedisFlaskIntegration(self.app, self.mock_calendar_sync)

        self.assertEqual(integration.app, self.app)
        self.assertEqual(integration.calendar_sync_callback, self.mock_calendar_sync)
        self.assertIsNotNone(integration.subscriber)

    @patch("redis_integration.flask_integration.create_redis_subscriber")
    def test_redis_status_endpoint(self, mock_create_subscriber):
        """Test /redis-status endpoint."""
        mock_subscriber = Mock()
        mock_subscriber.get_status.return_value = {"enabled": True, "connected": True}
        mock_subscriber.start_subscription.return_value = True
        mock_create_subscriber.return_value = mock_subscriber

        RedisFlaskIntegration(self.app, self.mock_calendar_sync)

        with self.app.test_client() as client:
            response = client.get("/redis-status")
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertTrue(data["success"])
            self.assertIn("redis_status", data)

    @patch("redis_integration.flask_integration.create_redis_subscriber")
    def test_manual_sync_endpoint(self, mock_create_subscriber):
        """Test /manual-sync endpoint."""
        mock_subscriber = Mock()
        mock_subscriber.start_subscription.return_value = True
        mock_create_subscriber.return_value = mock_subscriber

        RedisFlaskIntegration(self.app, self.mock_calendar_sync)

        with self.app.test_client() as client:
            response = client.post(
                "/manual-sync",
                json={"matches": [{"matchid": 123456}]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            data = json.loads(response.data)
            self.assertTrue(data["success"])
            self.assertEqual(data["matches_processed"], 1)

            # Should have called calendar sync
            self.assertEqual(len(self.calendar_sync_calls), 1)


if __name__ == "__main__":
    unittest.main()
