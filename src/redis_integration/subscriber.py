#!/usr/bin/env python3
"""
Redis Subscriber for Calendar Service

Provides Redis pub/sub subscription functionality for receiving real-time
match updates from the match processor service with Enhanced Schema v2.0 support.
"""

import json
import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional

from .logo_service import LogoServiceClient

logger = logging.getLogger(__name__)

# Check if Redis is available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - pub/sub functionality disabled")


class RedisSubscriber:
    """Redis subscriber for calendar service with Enhanced Schema v2.0 support."""

    def __init__(
        self,
        config,
        calendar_sync_callback: Callable[[List[Dict]], bool] = None,
        logo_service_client: Optional[LogoServiceClient] = None,
    ):
        """
        Initialize Redis subscriber.

        Args:
            config: Redis configuration
            calendar_sync_callback: Callback function for calendar sync
            logo_service_client: Optional logo service client for Enhanced Schema v2.0
        """
        self.config = config
        self.calendar_sync_callback = calendar_sync_callback
        self.logo_service_client = logo_service_client
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

        # Schema version statistics
        self.schema_v2_messages = 0
        self.schema_v1_messages = 0
        self.schema_unknown_messages = 0

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
        """Handle incoming Redis message with schema version detection."""
        self.messages_received += 1  # Count all received messages

        try:
            data = json.loads(message["data"])
            message_type = data.get("type")
            schema_version = data.get("schema_version", "1.0")

            # Route based on schema version
            if message_type == "match_updates":
                if schema_version == "2.0":
                    self.schema_v2_messages += 1
                    logger.info("📨 Received Enhanced Schema v2.0 message")
                    self._handle_enhanced_schema_v2(data)
                elif schema_version in ["1.5", "1.0"]:
                    self.schema_v1_messages += 1
                    logger.info(f"📨 Received Schema v{schema_version} message")
                    self._handle_legacy_schema(data, schema_version)
                else:
                    self.schema_unknown_messages += 1
                    logger.warning(
                        f"⚠️ Unknown schema version: {schema_version}, using legacy handler"
                    )
                    self._handle_legacy_schema(data, schema_version)
            else:
                logger.info(f"📨 Received {message_type} message")

            self.messages_processed += 1  # Count successfully processed messages

        except Exception as e:
            self.errors += 1  # Count errors
            logger.error(f"❌ Error handling message: {e}")

    def _handle_enhanced_schema_v2(self, data):
        """
        Handle Enhanced Schema v2.0 match update messages.

        Enhanced Schema v2.0 includes:
        - Complete contact information (mobile, email, address)
        - Team Organization IDs for logo generation
        - Detailed change information with priorities
        - Structured venue data with coordinates
        """
        try:
            payload = data.get("payload", {})
            matches = payload.get("matches", [])
            detailed_changes = payload.get("detailed_changes", [])
            metadata = payload.get("metadata", {})

            if not metadata.get("has_changes", False):
                logger.info("📋 No changes detected - skipping calendar sync")
                return

            logger.info(f"🗓️ Processing Enhanced Schema v2.0: {len(matches)} matches")

            # Enrich matches with logo paths if logo service is available
            if self.logo_service_client:
                matches = self._enrich_matches_with_logos(matches)

            # Determine sync priority based on change types
            high_priority = self._has_high_priority_changes(detailed_changes)

            if self.calendar_sync_callback:
                # Pass enriched matches with schema version indicator
                enriched_data = {
                    "matches": matches,
                    "schema_version": "2.0",
                    "detailed_changes": detailed_changes,
                    "high_priority": high_priority,
                }

                logger.info(
                    f"🗓️ Triggering {'immediate' if high_priority else 'standard'} "
                    f"calendar sync for {len(matches)} matches"
                )

                success = self.calendar_sync_callback(enriched_data)

                if success:
                    logger.info("✅ Enhanced Schema v2.0 calendar sync completed successfully")
                else:
                    logger.error("❌ Enhanced Schema v2.0 calendar sync failed")
            else:
                logger.warning("⚠️ No calendar sync callback configured")

        except Exception as e:
            logger.error(f"❌ Error processing Enhanced Schema v2.0 match updates: {e}")

    def _handle_legacy_schema(self, data, schema_version: str):
        """
        Handle legacy schema (v1.0, v1.5) match update messages.

        Maintains backward compatibility with existing message formats.
        """
        try:
            payload = data.get("payload", {})
            matches = payload.get("matches", [])
            metadata = payload.get("metadata", {})

            if not metadata.get("has_changes", False):
                logger.info("📋 No changes detected - skipping calendar sync")
                return

            if self.calendar_sync_callback:
                logger.info(
                    f"🗓️ Triggering calendar sync for {len(matches)} matches (v{schema_version})"
                )

                # For backward compatibility, pass matches directly or wrapped
                # Check if callback expects enriched data or simple list
                try:
                    # Try enriched format first
                    enriched_data = {
                        "matches": matches,
                        "schema_version": schema_version,
                        "detailed_changes": [],
                        "high_priority": False,
                    }
                    success = self.calendar_sync_callback(enriched_data)
                except TypeError:
                    # Fallback to simple list format for old callbacks
                    success = self.calendar_sync_callback(matches)

                if success:
                    logger.info("✅ Calendar sync completed successfully")
                else:
                    logger.error("❌ Calendar sync failed")
            else:
                logger.warning("⚠️ No calendar sync callback configured")

        except Exception as e:
            logger.error(f"❌ Error processing legacy schema match updates: {e}")

    def _enrich_matches_with_logos(self, matches: List[Dict]) -> List[Dict]:
        """
        Enrich matches with combined team logos.

        Args:
            matches: List of match dictionaries

        Returns:
            Enriched matches with logo_path field
        """
        enriched_matches = []

        for match in matches:
            enriched_match = match.copy()

            try:
                # Extract Organization IDs from Enhanced Schema v2.0 structure
                teams = match.get("teams", {})
                home_team = teams.get("home", {})
                away_team = teams.get("away", {})

                home_org_id = home_team.get("organization_id") or home_team.get("logo_id")
                away_org_id = away_team.get("organization_id") or away_team.get("logo_id")

                if home_org_id and away_org_id:
                    logo_path = self.logo_service_client.generate_combined_logo(
                        home_org_id, away_org_id
                    )

                    if logo_path:
                        enriched_match["logo_path"] = logo_path
                        logger.debug(f"✅ Logo generated for match {match.get('match_id')}")
                    else:
                        logger.debug(f"⚠️ Logo generation failed for match {match.get('match_id')}")
                else:
                    logger.debug(
                        f"⚠️ Missing Organization IDs for match {match.get('match_id')}: "
                        f"home={home_org_id}, away={away_org_id}"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Error enriching match with logo: {e}")

            enriched_matches.append(enriched_match)

        return enriched_matches

    def _has_high_priority_changes(self, detailed_changes: List[Dict]) -> bool:
        """
        Determine if changes include high-priority items.

        High-priority changes include:
        - Time changes
        - Date changes
        - Venue changes
        - Referee changes

        Args:
            detailed_changes: List of detailed change dictionaries

        Returns:
            True if high-priority changes exist
        """
        if not detailed_changes:
            return False

        high_priority_categories = ["time_change", "date_change", "venue_change", "referee_change"]

        for change in detailed_changes:
            if change.get("priority") == "high":
                return True
            if change.get("category") in high_priority_categories:
                return True

        return False

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
        """Get subscriber statistics including schema version breakdown."""
        uptime = time.time() - self.start_time
        return {
            "messages_processed": self.messages_processed,
            "messages_received": self.messages_received,
            "errors": self.errors,
            "reconnect_count": self.reconnect_count,
            "uptime": uptime,
            "last_message_time": None,  # Could be enhanced to track last message time
            "subscribed_channels": list(self.config.channels.values()),
            "subscription_stats": {
                "total_messages_received": self.messages_received,
                "successful_messages": self.messages_processed,
                "connected": self.client is not None,
                "subscribed": self.running,
            },
            "schema_version_stats": {
                "v2_messages": self.schema_v2_messages,
                "v1_messages": self.schema_v1_messages,
                "unknown_messages": self.schema_unknown_messages,
                "preferred_schema": self.config.schema_version,
            },
            "logo_service": {
                "enabled": self.logo_service_client is not None,
                "cache_size": (
                    self.logo_service_client.get_cache_size() if self.logo_service_client else 0
                ),
            },
        }


def create_redis_subscriber(
    config, calendar_sync_callback=None, logo_service_client=None
) -> RedisSubscriber:
    """
    Create Redis subscriber instance with Enhanced Schema v2.0 support.

    Args:
        config: Redis configuration
        calendar_sync_callback: Callback function for calendar sync
        logo_service_client: Optional logo service client for Enhanced Schema v2.0

    Returns:
        RedisSubscriber instance
    """
    return RedisSubscriber(config, calendar_sync_callback, logo_service_client)
