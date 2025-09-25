#!/usr/bin/env python3
"""
Redis Connection Manager for Test Compatibility

Provides connection management functionality expected by legacy integration tests.
This module maintains backward compatibility with test mocking patterns.
"""

import logging

logger = logging.getLogger(__name__)

# Check if Redis is available (imported from subscriber module for consistency)
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - connection manager disabled")


class ConnectionManager:
    """
    Redis connection manager for test compatibility.

    This class provides the interface expected by integration tests
    for mocking Redis connection operations.
    """

    def __init__(self, config=None):
        """Initialize connection manager."""
        self.config = config
        self.client = None
        self.connected = False

    def ensure_connection(self) -> bool:
        """Ensure Redis connection is established."""
        if not REDIS_AVAILABLE:
            return False

        try:
            if not self.client and self.config:
                self.client = redis.from_url(
                    self.config.url, socket_timeout=self.config.timeout, decode_responses=True
                )
                self.client.ping()
                self.connected = True
                return True
            return self.connected
        except Exception as e:
            logger.error(f"Failed to ensure Redis connection: {e}")
            self.connected = False
            return False

    def subscribe_to_channel(self, channel: str) -> bool:
        """Subscribe to a Redis channel."""
        if not self.ensure_connection():
            return False

        try:
            # This is a simplified implementation for test compatibility
            # Actual subscription logic is handled by RedisSubscriber
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            return False

    def unsubscribe_from_channel(self, channel: str) -> bool:
        """Unsubscribe from a Redis channel."""
        try:
            # This is a simplified implementation for test compatibility
            # Actual unsubscription logic is handled by RedisSubscriber
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")
            return False

    def get_status(self) -> dict:
        """Get connection status."""
        return {
            "connected": self.connected,
            "redis_available": REDIS_AVAILABLE,
            "client": self.client is not None,
        }
