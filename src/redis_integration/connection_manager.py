#!/usr/bin/env python3
"""
Redis Connection Manager for Calendar Service

This module provides Redis connection management with automatic reconnection,
health monitoring, and subscription management for the calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis connection management for calendar service
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class RedisSubscriptionConfig:
    """Configuration for Redis subscription."""

    url: str = "redis://fogis-redis:6379"
    decode_responses: bool = True
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    subscription_timeout: int = 1  # Timeout for subscription operations


class RedisSubscriptionManager:
    """Manages Redis subscriptions with automatic reconnection and health monitoring."""

    def __init__(self, config: RedisSubscriptionConfig = None):
        """
        Initialize Redis subscription manager.

        Args:
            config: Redis subscription configuration
        """
        self.config = config or RedisSubscriptionConfig()
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.last_health_check = datetime.min
        self.connection_attempts = 0
        self.is_connected = False
        self.is_subscribed = False
        self.last_error: Optional[str] = None
        self.subscribed_channels = set()
        self.subscription_thread: Optional[threading.Thread] = None
        self.stop_subscription = threading.Event()

        logger.info("🔧 Redis Subscription Manager initialized")
        logger.info(f"   Redis URL: {self.config.url}")
        logger.info(f"   Redis Available: {REDIS_AVAILABLE}")

        if REDIS_AVAILABLE:
            self._connect()
        else:
            logger.warning(
                "⚠️ Redis package not available - Redis functionality disabled"
            )

    def _connect(self) -> bool:
        """
        Establish Redis connection with retry logic.

        Returns:
            bool: True if connection successful
        """
        if not REDIS_AVAILABLE:
            return False

        try:
            logger.debug(
                f"🔌 Attempting Redis connection (attempt {self.connection_attempts + 1})"
            )

            self.client = redis.from_url(
                self.config.url,
                decode_responses=self.config.decode_responses,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
            )

            # Test connection
            self.client.ping()

            # Create pubsub instance
            self.pubsub = self.client.pubsub()

            self.is_connected = True
            self.last_error = None
            self.connection_attempts = 0
            self.last_health_check = datetime.now()

            logger.info("✅ Redis subscription connection established successfully")
            return True

        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            self.connection_attempts += 1

            logger.warning(
                f"⚠️ Redis subscription connection failed (attempt {self.connection_attempts}): {e}"
            )
            return False

    def ensure_connection(self) -> bool:
        """
        Ensure Redis connection is active, reconnect if necessary.

        Returns:
            bool: True if connection is active
        """
        if not REDIS_AVAILABLE:
            return False

        # Check if we need to perform health check
        now = datetime.now()
        if (now - self.last_health_check).seconds >= self.config.health_check_interval:
            self._health_check()

        # If not connected, try to reconnect
        if not self.is_connected:
            if self.connection_attempts < self.config.max_retries:
                time.sleep(self.config.retry_delay)
                return self._connect()
            else:
                logger.error(
                    f"❌ Redis subscription connection failed after {self.config.max_retries} attempts"
                )
                return False

        return True

    def _health_check(self) -> bool:
        """
        Perform Redis health check.

        Returns:
            bool: True if Redis is healthy
        """
        if not REDIS_AVAILABLE or not self.client:
            return False

        try:
            self.client.ping()
            self.is_connected = True
            self.last_health_check = datetime.now()
            return True

        except Exception as e:
            logger.warning(f"⚠️ Redis subscription health check failed: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return False

    def subscribe_to_channel(
        self, channel: str, message_handler: Callable[[Dict], None]
    ) -> bool:
        """
        Subscribe to Redis channel with message handler.

        Args:
            channel: Redis channel name
            message_handler: Function to handle received messages

        Returns:
            bool: True if subscription successful
        """
        if not self.ensure_connection():
            logger.warning(f"⚠️ Cannot subscribe to {channel}: Redis not available")
            return False

        try:
            logger.info(f"📡 Subscribing to Redis channel: {channel}")

            # Subscribe to channel
            self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            self.is_subscribed = True

            # Start subscription thread if not already running
            if not self.subscription_thread or not self.subscription_thread.is_alive():
                self.stop_subscription.clear()
                self.subscription_thread = threading.Thread(
                    target=self._subscription_loop, args=(message_handler,), daemon=True
                )
                self.subscription_thread.start()

            logger.info(f"✅ Successfully subscribed to {channel}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {channel}: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return False

    def _subscription_loop(self, message_handler: Callable[[Dict], None]) -> None:
        """
        Main subscription loop for processing messages.

        Args:
            message_handler: Function to handle received messages
        """
        logger.info("🔄 Starting Redis subscription loop")

        while not self.stop_subscription.is_set():
            try:
                if not self.ensure_connection() or not self.pubsub:
                    time.sleep(self.config.retry_delay)
                    continue

                # Get message with timeout
                message = self.pubsub.get_message(
                    timeout=self.config.subscription_timeout
                )

                if message is not None:
                    # Skip subscription confirmation messages
                    if message["type"] == "message":
                        try:
                            # Parse message data
                            import json

                            message_data = json.loads(message["data"])

                            logger.debug(
                                f"📨 Received message on {message['channel']}: {message_data.get('type', 'unknown')}"
                            )

                            # Handle message
                            message_handler(message_data)

                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Failed to parse message JSON: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error handling message: {e}")

            except Exception as e:
                logger.error(f"❌ Error in subscription loop: {e}")
                self.is_connected = False
                time.sleep(self.config.retry_delay)

        logger.info("🔄 Redis subscription loop stopped")

    def unsubscribe_from_channel(self, channel: str) -> bool:
        """
        Unsubscribe from Redis channel.

        Args:
            channel: Redis channel name

        Returns:
            bool: True if unsubscription successful
        """
        if not self.pubsub:
            return False

        try:
            logger.info(f"📡 Unsubscribing from Redis channel: {channel}")

            self.pubsub.unsubscribe(channel)
            self.subscribed_channels.discard(channel)

            if not self.subscribed_channels:
                self.is_subscribed = False

            logger.info(f"✅ Successfully unsubscribed from {channel}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to unsubscribe from {channel}: {e}")
            return False

    def get_subscription_status(self) -> Dict[str, Any]:
        """
        Get current subscription status and statistics.

        Returns:
            Dict[str, Any]: Subscription status information
        """
        return {
            "redis_available": REDIS_AVAILABLE,
            "is_connected": self.is_connected,
            "is_subscribed": self.is_subscribed,
            "subscribed_channels": list(self.subscribed_channels),
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "last_health_check": (
                self.last_health_check.isoformat()
                if self.last_health_check != datetime.min
                else None
            ),
            "subscription_thread_alive": (
                self.subscription_thread.is_alive()
                if self.subscription_thread
                else False
            ),
            "config": {
                "url": self.config.url,
                "timeout": self.config.socket_timeout,
                "max_retries": self.config.max_retries,
            },
        }

    def close(self) -> None:
        """Close Redis subscription gracefully."""
        logger.info("🔌 Closing Redis subscription")

        # Stop subscription loop
        self.stop_subscription.set()

        # Wait for subscription thread to finish
        if self.subscription_thread and self.subscription_thread.is_alive():
            self.subscription_thread.join(timeout=5)

        # Close pubsub and client
        if self.pubsub:
            try:
                self.pubsub.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing pubsub: {e}")

        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing Redis client: {e}")

        self.client = None
        self.pubsub = None
        self.is_connected = False
        self.is_subscribed = False


# Convenience functions for external use
def create_redis_subscription_manager(
    redis_url: str = None,
) -> RedisSubscriptionManager:
    """
    Create Redis subscription manager with optional custom URL.

    Args:
        redis_url: Custom Redis URL (optional)

    Returns:
        RedisSubscriptionManager: Configured subscription manager
    """
    config = RedisSubscriptionConfig()
    if redis_url:
        config.url = redis_url

    return RedisSubscriptionManager(config)


def test_redis_subscription(redis_url: str = None) -> bool:
    """
    Test Redis subscription availability.

    Args:
        redis_url: Custom Redis URL (optional)

    Returns:
        bool: True if Redis is available and connectable
    """
    manager = create_redis_subscription_manager(redis_url)
    status = manager.ensure_connection()
    manager.close()
    return status


if __name__ == "__main__":
    # Test Redis subscription manager
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logger.info("🧪 Testing Redis subscription manager...")

    # Test connection
    if test_redis_subscription():
        logger.info("✅ Redis subscription test successful")
    else:
        logger.error("❌ Redis subscription test failed")

    manager.close()
