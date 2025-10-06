#!/usr/bin/env python3
"""
Redis Subscriber for Calendar Service

Provides Redis pub/sub subscription functionality for receiving real-time
match updates from the match processor service.
"""

import json
import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if Redis is available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - pub/sub functionality disabled")


class RedisSubscriber:
    """Simplified Redis subscriber for calendar service."""

    def __init__(self, config, calendar_sync_callback: Callable[[List[Dict]], bool] = None):
        """Initialize Redis subscriber."""
        self.config = config
        self.calendar_sync_callback = calendar_sync_callback
        self.client = None
        self.pubsub = None
        self.subscription_thread = None
        self.running = False

        # Message counting and statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.errors = 0
        self.reconnect_count = 0
        self.start_time = time.time()

        if REDIS_AVAILABLE and config.enabled:
            self._connect()

    def _connect(self) -> bool:
        """Connect to Redis with proper pub/sub configuration."""
        try:
            # Build socket keepalive options (platform-specific)
            keepalive_options = {}
            try:
                # Linux/Unix constants
                if hasattr(socket, "TCP_KEEPIDLE"):
                    keepalive_options[socket.TCP_KEEPIDLE] = 60
                if hasattr(socket, "TCP_KEEPINTVL"):
                    keepalive_options[socket.TCP_KEEPINTVL] = 10
                if hasattr(socket, "TCP_KEEPCNT"):
                    keepalive_options[socket.TCP_KEEPCNT] = 6
            except AttributeError:
                # Platform doesn't support these options
                pass

            self.client = redis.from_url(
                self.config.url,
                # ✅ FIX: No timeout for read operations (allows indefinite blocking)
                socket_timeout=None,
                # ✅ Timeout only for connection establishment
                socket_connect_timeout=5,
                # ✅ Enable TCP keepalive for connection health monitoring
                socket_keepalive=True,
                socket_keepalive_options=keepalive_options if keepalive_options else None,
                # ✅ Application-level health checks (redis-py 4.2+)
                health_check_interval=30,  # Ping every 30 seconds
                decode_responses=True,
            )
            self.client.ping()
            logger.info(f"✅ Connected to Redis: {self.config.url}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            return False

    def _reconnect(self) -> bool:
        """Reconnect to Redis and resubscribe to channels."""
        try:
            # Close old connections
            if self.pubsub:
                try:
                    self.pubsub.close()
                except Exception:
                    pass
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass

            # Create new connection
            if not self._connect():
                return False

            # Recreate pubsub and resubscribe
            self.pubsub = self.client.pubsub(ignore_subscribe_messages=True)
            for channel in self.config.channels.values():
                self.pubsub.subscribe(channel)
                logger.info(f"📡 Resubscribed to channel: {channel}")

            return True
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")
            return False

    def start_subscription(self) -> bool:
        """Start Redis subscription."""
        if not REDIS_AVAILABLE or not self.config.enabled or not self.client:
            return False

        try:
            self.pubsub = self.client.pubsub()

            # Subscribe to channels
            for channel in self.config.channels.values():
                self.pubsub.subscribe(channel)
                logger.info(f"📡 Subscribed to channel: {channel}")

            # Start subscription thread
            self.running = True
            self.subscription_thread = threading.Thread(target=self._listen_for_messages)
            self.subscription_thread.daemon = True
            self.subscription_thread.start()

            logger.info("✅ Redis subscription started")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start subscription: {e}")
            return False

    def _listen_for_messages(self):
        """Listen for Redis messages with auto-recovery."""
        retry_delay = 1
        max_retry_delay = 60

        while self.running:
            try:
                logger.info("🔄 Starting message listener...")

                # ✅ This blocks indefinitely (no timeout)
                for message in self.pubsub.listen():
                    if not self.running:
                        break
                    if message["type"] == "message":
                        self._handle_message(message)
                        retry_delay = 1  # Reset on success

                if not self.running:
                    break

            except redis.ConnectionError as e:
                # ✅ Only genuine connection failures reach here
                self.reconnect_count += 1
                logger.error(f"❌ Connection lost: {e}")
                logger.info(f"🔄 Reconnecting in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
                self._reconnect()

            except Exception as e:
                self.errors += 1
                logger.error(f"❌ Unexpected error: {e}", exc_info=True)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    def _handle_message(self, message):
        """Handle incoming Redis message."""
        self.messages_received += 1  # Count all received messages

        try:
            data = json.loads(message["data"])
            message_type = data.get("type")

            if message_type == "match_updates":
                self._handle_match_updates(data)
            else:
                logger.info(f"📨 Received {message_type} message")

            self.messages_processed += 1  # Count successfully processed messages

        except Exception as e:
            self.errors += 1  # Count errors
            logger.error(f"❌ Error handling message: {e}")

    def _handle_match_updates(self, data):
        """Handle match update messages."""
        try:
            payload = data.get("payload", {})
            matches = payload.get("matches", [])
            metadata = payload.get("metadata", {})

            if not metadata.get("has_changes", False):
                logger.info("📋 No changes detected - skipping calendar sync")
                return

            if self.calendar_sync_callback:
                logger.info(f"🗓️ Triggering calendar sync for {len(matches)} matches")
                success = self.calendar_sync_callback(matches)

                if success:
                    logger.info("✅ Calendar sync completed successfully")
                else:
                    logger.error("❌ Calendar sync failed")
            else:
                logger.warning("⚠️ No calendar sync callback configured")

        except Exception as e:
            logger.error(f"❌ Error processing match updates: {e}")

    def stop_subscription(self):
        """Stop Redis subscription."""
        self.running = False

        if self.pubsub:
            try:
                self.pubsub.close()
            except Exception:
                pass

        if self.subscription_thread and self.subscription_thread.is_alive():
            self.subscription_thread.join(timeout=1)

        logger.info("🛑 Redis subscription stopped")

    def get_status(self) -> Dict:
        """Get subscriber status."""
        return {
            "enabled": self.config.enabled,
            "connected": self.client is not None,
            "subscribed": self.running,
            "redis_available": REDIS_AVAILABLE,
        }

    def get_statistics(self) -> Dict:
        """Get subscriber statistics."""
        uptime = time.time() - self.start_time
        return {
            "messages_processed": self.messages_processed,
            "messages_received": self.messages_received,
            "errors": self.errors,
            "reconnect_count": self.reconnect_count,
            "uptime": uptime,
            "last_message_time": None,  # Could be enhanced to track last message time
            "subscribed_channels": ["fogis:matches:updates"],  # Default channel
            "subscription_stats": {
                "total_messages_received": self.messages_received,
                "successful_messages": self.messages_processed,
                "connected": self.client is not None,
                "subscribed": self.running,
            },
        }


def create_redis_subscriber(config, calendar_sync_callback=None) -> RedisSubscriber:
    """Create Redis subscriber instance."""
    return RedisSubscriber(config, calendar_sync_callback)
