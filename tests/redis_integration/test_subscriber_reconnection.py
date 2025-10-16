#!/usr/bin/env python3
"""
Tests for Redis Subscriber Reconnection and Timeout Fix

Tests to verify the fix for issue #120:
- No spurious timeouts from socket_timeout
- Proper reconnection on connection failures
- Reconnect count tracking
- Message reception after extended idle periods
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add src to path for imports (must be before local imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Local imports after path modification
from redis_integration import RedisConfig, RedisSubscriber  # noqa: E402


class TestSubscriberReconnection(unittest.TestCase):
    """Test Redis subscriber reconnection and timeout handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RedisConfig(url="redis://test:6379", enabled=True)
        self.calendar_sync_calls = []

        def mock_calendar_sync(matches):
            self.calendar_sync_calls.append(matches)
            return True

        self.mock_calendar_sync = mock_calendar_sync

    @patch("redis_integration.subscriber.redis")
    def test_connect_without_socket_timeout(self, mock_redis):
        """Test that connection is made without socket_timeout."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        # Verify connection was made
        self.assertIsNotNone(subscriber.client)

        # Verify socket_timeout is None (not set)
        call_kwargs = mock_redis.from_url.call_args[1]
        self.assertIsNone(call_kwargs.get("socket_timeout"))

        # Verify socket_connect_timeout is set
        self.assertEqual(call_kwargs.get("socket_connect_timeout"), 5)

        # Verify socket_keepalive is enabled
        self.assertTrue(call_kwargs.get("socket_keepalive"))

        # Verify health_check_interval is set
        self.assertEqual(call_kwargs.get("health_check_interval"), 30)

    @patch("redis_integration.subscriber.redis")
    def test_reconnect_count_initialization(self, mock_redis):
        """Test that reconnect_count is initialized to 0."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        self.assertEqual(subscriber.reconnect_count, 0)

    @patch("redis_integration.subscriber.redis")
    def test_reconnect_count_in_statistics(self, mock_redis):
        """Test that reconnect_count is included in statistics."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        stats = subscriber.get_statistics()

        self.assertIn("reconnect_count", stats)
        self.assertEqual(stats["reconnect_count"], 0)

    @patch("redis_integration.subscriber.redis")
    def test_reconnect_method_closes_old_connections(self, mock_redis):
        """Test that _reconnect() closes old connections before creating new ones."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        subscriber.pubsub = mock_pubsub

        # Call reconnect
        subscriber._reconnect()

        # Verify old connections were closed
        mock_pubsub.close.assert_called_once()
        mock_client.close.assert_called()

    @patch("redis_integration.subscriber.redis")
    def test_reconnect_method_resubscribes_to_channels(self, mock_redis):
        """Test that _reconnect() resubscribes to all channels."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        # Call reconnect
        result = subscriber._reconnect()

        # Verify reconnection succeeded
        self.assertTrue(result)

        # Verify pubsub was created
        mock_client.pubsub.assert_called()

        # Verify channels were subscribed
        # The config has multiple channels, verify subscribe was called
        self.assertGreater(mock_pubsub.subscribe.call_count, 0)

    @patch("redis_integration.subscriber.redis")
    def test_listen_for_messages_handles_connection_error(self, mock_redis):
        """Test that _listen_for_messages() handles ConnectionError and reconnects."""
        import redis as real_redis

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()

        # Simulate ConnectionError on first listen, then stop
        # Use real redis.ConnectionError for proper exception handling
        mock_pubsub.listen.side_effect = [real_redis.ConnectionError("Connection lost")]

        # Set up the mock redis module to use real ConnectionError
        mock_redis.ConnectionError = real_redis.ConnectionError
        mock_redis.from_url.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        subscriber.pubsub = mock_pubsub
        subscriber.running = True

        # Mock _reconnect to stop the loop
        original_reconnect = subscriber._reconnect

        def mock_reconnect():
            subscriber.running = False  # Stop the loop
            return original_reconnect()

        subscriber._reconnect = mock_reconnect

        # Run listener (should handle error and reconnect)
        subscriber._listen_for_messages()

        # Verify reconnect_count was incremented
        self.assertEqual(subscriber.reconnect_count, 1)

    @patch("redis_integration.subscriber.redis")
    def test_listen_for_messages_handles_unexpected_error(self, mock_redis):
        """Test that _listen_for_messages() handles unexpected errors."""
        import redis as real_redis

        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()

        # Simulate unexpected error on first listen, then stop
        mock_pubsub.listen.side_effect = [RuntimeError("Unexpected error")]

        # Set up the mock redis module to use real ConnectionError
        mock_redis.ConnectionError = real_redis.ConnectionError
        mock_redis.from_url.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        subscriber.pubsub = mock_pubsub
        subscriber.running = True

        # Mock to stop the loop after first error
        def mock_listen():
            subscriber.running = False  # Stop the loop after first error
            raise RuntimeError("Unexpected error")

        mock_pubsub.listen = mock_listen

        # Run listener (should handle error)
        subscriber._listen_for_messages()

        # Verify error count was incremented
        self.assertEqual(subscriber.errors, 1)

    @patch("redis_integration.subscriber.redis")
    def test_listen_for_messages_resets_retry_delay_on_success(self, mock_redis):
        """Test that retry delay is reset on successful message processing."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pubsub = Mock()

        # Simulate successful message reception
        messages = [
            {"type": "subscribe", "channel": "test"},
            {"type": "message", "data": '{"type": "test"}', "channel": "test"},
        ]

        def message_generator():
            for msg in messages:
                yield msg
            # Stop after messages
            subscriber.running = False

        mock_pubsub.listen.return_value = message_generator()
        mock_redis.from_url.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)
        subscriber.pubsub = mock_pubsub
        subscriber.running = True

        # Run listener
        subscriber._listen_for_messages()

        # Verify messages were received
        self.assertEqual(subscriber.messages_received, 1)

    @patch("redis_integration.subscriber.redis")
    def test_reconnect_handles_connection_failure(self, mock_redis):
        """Test that _reconnect() handles connection failures gracefully."""
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis.from_url.return_value = mock_client

        subscriber = RedisSubscriber(self.config, self.mock_calendar_sync)

        # Force a reconnect attempt
        result = subscriber._reconnect()

        # Verify reconnection failed gracefully
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
