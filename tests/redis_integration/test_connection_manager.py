#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Connection Manager

This module provides comprehensive tests for the Redis connection management functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis connection manager
"""

import logging
import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.connection_manager import (  # noqa: E402
    RedisSubscriptionConfig,
    RedisSubscriptionManager,
    create_redis_subscription_manager,
)


class TestRedisSubscriptionConfig(unittest.TestCase):
    """Test cases for RedisSubscriptionConfig."""

    def test_subscription_config_creation_with_defaults(self):
        """Test subscription config creation with default values."""
        config = RedisSubscriptionConfig()

        self.assertIsInstance(config.channels, list)
        self.assertIsInstance(config.patterns, list)
        self.assertIsInstance(config.ignore_subscribe_messages, bool)

    def test_subscription_config_creation_with_custom_values(self):
        """Test subscription config creation with custom values."""
        channels = ["test:channel1", "test:channel2"]
        patterns = ["test:*", "match:*"]

        config = RedisSubscriptionConfig(
            channels=channels, patterns=patterns, ignore_subscribe_messages=False
        )

        self.assertEqual(config.channels, channels)
        self.assertEqual(config.patterns, patterns)
        self.assertFalse(config.ignore_subscribe_messages)


class TestRedisSubscriptionManager(unittest.TestCase):
    """Test cases for RedisSubscriptionManager."""

    def setUp(self):
        """Set up test fixtures."""
        config = RedisSubscriptionConfig(url="redis://test_host:6379")
        self.manager = RedisSubscriptionManager(config)

    def test_connection_manager_initialization(self):
        """Test connection manager initialization."""
        self.assertIsInstance(self.manager, RedisSubscriptionManager)
        self.assertEqual(self.manager.config.url, "redis://test_host:6379")

    def test_connection_manager_default_config(self):
        """Test connection manager with default configuration."""
        manager = RedisSubscriptionManager()

        self.assertIsInstance(manager, RedisSubscriptionManager)

    def test_connect_success(self):
        """Test successful Redis connection."""
        with patch("redis.from_url") as mock_redis_from_url:
            mock_connection = Mock()
            mock_connection.ping.return_value = True
            mock_redis_from_url.return_value = mock_connection

            result = self.manager._connect()

            self.assertTrue(result)

    def test_connect_failure(self):
        """Test Redis connection failure."""
        with patch("redis.from_url") as mock_redis_from_url:
            mock_redis_from_url.side_effect = Exception("Connection failed")

            result = self.manager._connect()

            self.assertFalse(result)

    def test_connect_ping_failure(self):
        """Test Redis connection with ping failure."""
        with patch("redis.from_url") as mock_redis_from_url:
            mock_connection = Mock()
            mock_connection.ping.side_effect = Exception("Ping failed")
            mock_redis_from_url.return_value = mock_connection

            result = self.manager._connect()

            self.assertFalse(result)

    def test_close_connection(self):
        """Test closing Redis connection."""
        mock_connection = Mock()
        self.manager.redis_client = mock_connection

        self.manager.close()

        mock_connection.close.assert_called_once()

    def test_close_no_connection(self):
        """Test closing when no connection exists."""
        self.manager.redis_client = None

        # Should not raise exception
        self.manager.close()

    def test_close_with_exception(self):
        """Test closing connection with exception."""
        mock_connection = Mock()
        mock_connection.close.side_effect = Exception("Close failed")
        self.manager.redis_client = mock_connection

        # Should not raise exception
        self.manager.close()

    def test_health_check_success(self):
        """Test successful health check."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        self.manager.redis_client = mock_connection

        result = self.manager._health_check()

        self.assertTrue(result)

    def test_health_check_not_connected(self):
        """Test health check when not connected."""
        self.manager.redis_client = None

        result = self.manager._health_check()

        self.assertFalse(result)

    def test_health_check_ping_failure(self):
        """Test health check with ping failure."""
        mock_connection = Mock()
        mock_connection.ping.side_effect = Exception("Ping failed")
        self.manager.redis_client = mock_connection

        result = self.manager._health_check()

        self.assertFalse(result)

    def test_subscription_start_success(self):
        """Test successful subscription start."""
        mock_connection = Mock()
        mock_pubsub = Mock()
        mock_connection.pubsub.return_value = mock_pubsub
        self.manager.redis_client = mock_connection

        result = self.manager.start_subscription(["test:channel"])

        self.assertTrue(result)

    def test_subscription_when_not_connected(self):
        """Test subscription when not connected."""
        self.manager.redis_client = None

        result = self.manager.start_subscription(["test:channel"])

        self.assertFalse(result)

    def test_subscription_stop_success(self):
        """Test successful subscription stop."""
        mock_pubsub = Mock()
        self.manager.pubsub = mock_pubsub

        self.manager.stop_subscription()

        mock_pubsub.close.assert_called_once()

    def test_subscription_status(self):
        """Test getting subscription status."""
        status = self.manager.get_subscription_status()

        self.assertIsInstance(status, dict)
        self.assertIn("is_connected", status)
        self.assertIn("is_subscribed", status)

    def test_get_subscription_message(self):
        """Test getting subscription message."""
        mock_pubsub = Mock()
        mock_pubsub.get_message.return_value = {"type": "message", "data": b"test"}
        self.manager.pubsub = mock_pubsub

        message = self.manager.get_message()

        self.assertIsNotNone(message)

    def test_get_subscription_message_no_pubsub(self):
        """Test getting message when no pubsub."""
        self.manager.pubsub = None

        message = self.manager.get_message()

        self.assertIsNone(message)


class TestConnectionHelperFunctions(unittest.TestCase):
    """Test cases for connection helper functions."""

    def test_create_redis_connection_function(self):
        """Test create_redis_connection helper function."""
        connection = create_redis_subscription_manager(redis_url="redis://test:6379")

        self.assertIsInstance(connection, RedisSubscriptionManager)


if __name__ == "__main__":
    unittest.main()
