#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Configuration

This module provides comprehensive tests for the Redis configuration functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis configuration
"""

import logging
import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.config import (  # noqa: E402
    RedisSubscriptionConfig,
    RedisSubscriptionConfigManager,
    get_redis_subscription_config,
    get_redis_subscription_config_manager,
    reload_redis_subscription_config,
)


class TestRedisSubscriptionConfig(unittest.TestCase):
    """Test cases for RedisSubscriptionConfig."""

    def test_redis_config_creation_with_defaults(self):
        """Test Redis config creation with default values."""
        config = RedisSubscriptionConfig()

        self.assertIsInstance(config.url, str)
        self.assertIsInstance(config.enabled, bool)
        self.assertIsInstance(config.socket_connect_timeout, int)
        self.assertIsInstance(config.socket_timeout, int)
        self.assertIsInstance(config.retry_on_timeout, bool)
        self.assertIsInstance(config.max_retries, int)
        self.assertIsInstance(config.retry_delay, float)
        self.assertIsInstance(config.health_check_interval, int)

    def test_redis_config_creation_with_custom_values(self):
        """Test Redis config creation with custom values."""
        config = RedisSubscriptionConfig(
            url="redis://custom:6379",
            enabled=False,
            socket_connect_timeout=10,
            socket_timeout=15,
            retry_on_timeout=False,
            max_retries=5,
            retry_delay=2.0,
            health_check_interval=60,
        )

        self.assertEqual(config.url, "redis://custom:6379")
        self.assertFalse(config.enabled)
        self.assertEqual(config.socket_connect_timeout, 10)
        self.assertEqual(config.socket_timeout, 15)
        self.assertFalse(config.retry_on_timeout)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.retry_delay, 2.0)
        self.assertEqual(config.health_check_interval, 60)

    def test_redis_config_channels(self):
        """Test Redis config channel properties."""
        config = RedisSubscriptionConfig()

        self.assertIsInstance(config.url, str)
        self.assertIsInstance(config.decode_responses, bool)

    def test_redis_config_to_dict(self):
        """Test converting Redis config to dictionary."""
        config = RedisSubscriptionConfig()

        config_dict = config.to_dict()

        self.assertIsInstance(config_dict, dict)
        self.assertIn("url", config_dict)
        self.assertIn("enabled", config_dict)

    def test_redis_config_from_environment(self):
        """Test creating Redis config from environment variables."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://env:6379", "REDIS_ENABLED": "false"}):
            config = RedisSubscriptionConfig.from_environment()

            self.assertEqual(config.url, "redis://env:6379")
            self.assertFalse(config.enabled)

    def test_redis_config_environment_parsing(self):
        """Test environment variable parsing."""
        with patch.dict(
            os.environ,
            {"REDIS_ENABLED": "true", "REDIS_MAX_RETRIES": "10", "REDIS_RETRY_DELAY": "3.5"},
        ):
            config = RedisSubscriptionConfig.from_environment()

            self.assertTrue(config.enabled)
            self.assertEqual(config.max_retries, 10)
            self.assertEqual(config.retry_delay, 3.5)

    def test_redis_config_equality(self):
        """Test Redis config equality comparison."""
        config1 = RedisSubscriptionConfig(url="redis://test:6379", enabled=True)
        config2 = RedisSubscriptionConfig(url="redis://test:6379", enabled=True)
        config3 = RedisSubscriptionConfig(url="redis://other:6379", enabled=True)

        self.assertEqual(config1, config2)
        self.assertNotEqual(config1, config3)

    def test_redis_config_str_representation(self):
        """Test Redis config string representation."""
        config = RedisSubscriptionConfig()

        config_str = str(config)

        self.assertIsInstance(config_str, str)
        self.assertIn("RedisSubscriptionConfig", config_str)

    def test_redis_config_repr_representation(self):
        """Test Redis config repr representation."""
        config = RedisSubscriptionConfig()

        config_repr = repr(config)

        self.assertIsInstance(config_repr, str)
        self.assertIn("RedisSubscriptionConfig", config_repr)


class TestRedisSubscriptionConfigManager(unittest.TestCase):
    """Test cases for RedisSubscriptionConfigManager."""

    def test_redis_config_manager_initialization(self):
        """Test Redis config manager initialization."""
        manager = RedisSubscriptionConfigManager()

        self.assertIsInstance(manager, RedisSubscriptionConfigManager)
        self.assertIsInstance(manager.config, RedisSubscriptionConfig)

    def test_redis_config_manager_with_custom_config(self):
        """Test Redis config manager with custom config."""
        custom_config = RedisSubscriptionConfig(url="redis://custom:6379")
        manager = RedisSubscriptionConfigManager(custom_config)

        self.assertEqual(manager.config.url, "redis://custom:6379")

    def test_redis_config_manager_reload(self):
        """Test Redis config manager reload."""
        manager = RedisSubscriptionConfigManager()

        manager.reload_from_environment()

        # Config should be reloaded from environment
        self.assertIsInstance(manager.config, RedisSubscriptionConfig)

    def test_redis_config_manager_update(self):
        """Test Redis config manager update."""
        manager = RedisSubscriptionConfigManager()
        new_config = RedisSubscriptionConfig(url="redis://updated:6379")

        manager.update_config(new_config)

        self.assertEqual(manager.config.url, "redis://updated:6379")

    def test_redis_config_manager_validate(self):
        """Test Redis config manager validation."""
        manager = RedisSubscriptionConfigManager()

        # Should not raise exception for valid config
        is_valid = manager.is_valid()

        self.assertIsInstance(is_valid, bool)


class TestConfigHelperFunctions(unittest.TestCase):
    """Test cases for config helper functions."""

    def test_get_redis_config_function(self):
        """Test get_redis_config helper function."""
        config = get_redis_subscription_config()

        self.assertIsInstance(config, RedisSubscriptionConfig)

    def test_get_redis_config_manager_function(self):
        """Test get_redis_config_manager helper function."""
        manager = get_redis_subscription_config_manager()

        self.assertIsInstance(manager, RedisSubscriptionConfigManager)

    def test_reload_redis_config_function(self):
        """Test reload_redis_config helper function."""
        # Should not raise exception
        reload_redis_subscription_config()


if __name__ == "__main__":
    unittest.main()
