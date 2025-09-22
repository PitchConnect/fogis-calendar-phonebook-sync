#!/usr/bin/env python3
"""
Redis Service Integration for Calendar Service

This module provides high-level Redis service integration for the FOGIS calendar service,
coordinating Redis subscription with the existing calendar synchronization workflow.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis service integration for calendar service
"""

import logging
import os
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .connection_manager import RedisSubscriptionConfig
from .subscriber import CalendarServiceRedisSubscriber

logger = logging.getLogger(__name__)


class CalendarServiceRedisService:
    """High-level Redis service integration for calendar service."""

    def __init__(
        self,
        redis_url: str = None,
        enabled: bool = None,
        calendar_sync_callback: Callable[[List[Dict]], bool] = None,
    ):
        """
        Initialize Redis service integration for calendar service.

        Args:
            redis_url: Redis connection URL (optional, uses environment variable if not provided)
            enabled: Whether Redis integration is enabled (optional, uses environment variable if not provided)
            calendar_sync_callback: Function to call for calendar synchronization
        """
        # Configuration from environment variables
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://fogis-redis:6379")
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("REDIS_PUBSUB_ENABLED", "true").lower() == "true"
        )
        self.calendar_sync_callback = calendar_sync_callback

        # Initialize subscriber if enabled
        self.subscriber: Optional[CalendarServiceRedisSubscriber] = None
        self.initialization_error: Optional[str] = None
        self.service_lock = threading.Lock()

        logger.info("🔧 Calendar Service Redis Service initializing...")
        logger.info(f"   Redis URL: {self.redis_url}")
        logger.info(f"   Enabled: {self.enabled}")

        if self.enabled:
            self._initialize_redis_subscriber()
        else:
            logger.info("📋 Redis integration disabled by configuration")

    def _initialize_redis_subscriber(self) -> bool:
        """
        Initialize Redis subscriber with error handling.

        Returns:
            bool: True if initialization successful
        """
        try:
            config = RedisSubscriptionConfig(url=self.redis_url)
            self.subscriber = CalendarServiceRedisSubscriber(config, self.calendar_sync_callback)

            logger.info("✅ Redis subscriber initialized successfully")
            return True

        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"❌ Failed to initialize Redis subscriber: {e}")
            logger.warning("⚠️ Redis integration will be disabled for this session")
            return False

    def start_redis_subscription(self, channels: List[str] = None) -> bool:
        """
        Start Redis subscription for calendar service.

        Args:
            channels: List of channel names to subscribe to (optional)

        Returns:
            bool: True if subscription started successfully
        """
        if not self.enabled:
            logger.info("📋 Redis subscription disabled by configuration")
            return False

        if not self.subscriber:
            logger.warning("⚠️ Redis subscriber not initialized")
            return False

        with self.service_lock:
            try:
                logger.info("🚀 Starting Redis subscription for calendar service...")

                # Start subscription
                success = self.subscriber.start_subscription(channels)

                if success:
                    logger.info("✅ Redis subscription started successfully")
                    logger.info("📡 Calendar service is now receiving real-time match updates")
                    return True
                else:
                    logger.error("❌ Failed to start Redis subscription")
                    return False

            except Exception as e:
                logger.error(f"❌ Failed to start Redis subscription: {e}")
                return False

    def stop_redis_subscription(self, channels: List[str] = None) -> bool:
        """
        Stop Redis subscription for calendar service.

        Args:
            channels: List of channel names to unsubscribe from (optional)

        Returns:
            bool: True if subscription stopped successfully
        """
        if not self.enabled or not self.subscriber:
            return True

        with self.service_lock:
            try:
                logger.info("🛑 Stopping Redis subscription for calendar service...")

                success = self.subscriber.stop_subscription(channels)

                if success:
                    logger.info("✅ Redis subscription stopped successfully")
                    return True
                else:
                    logger.error("❌ Failed to stop Redis subscription")
                    return False

            except Exception as e:
                logger.error(f"❌ Failed to stop Redis subscription: {e}")
                return False

    def set_calendar_sync_callback(self, callback: Callable[[List[Dict]], bool]) -> None:
        """
        Set or update the calendar synchronization callback.

        Args:
            callback: Function to call for calendar synchronization
        """
        self.calendar_sync_callback = callback

        if self.subscriber and self.subscriber.match_handler:
            self.subscriber.match_handler.calendar_sync_callback = callback
            logger.info("✅ Calendar sync callback updated")

    def handle_manual_sync_request(self, matches: List[Dict[str, Any]]) -> bool:
        """
        Handle manual calendar sync request (fallback for HTTP endpoints).

        Args:
            matches: List of match dictionaries to sync

        Returns:
            bool: True if sync successful
        """
        try:
            logger.info(f"📅 Processing manual calendar sync request for {len(matches)} matches")

            if self.calendar_sync_callback:
                success = self.calendar_sync_callback(matches)

                if success:
                    logger.info("✅ Manual calendar sync completed successfully")
                    return True
                else:
                    logger.error("❌ Manual calendar sync failed")
                    return False
            else:
                logger.warning("⚠️ No calendar sync callback configured")
                return False

        except Exception as e:
            logger.error(f"❌ Manual calendar sync error: {e}")
            return False

    def get_redis_status(self) -> Dict[str, Any]:
        """
        Get comprehensive Redis service status.

        Returns:
            Dict[str, Any]: Redis service status information
        """
        if not self.enabled:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Redis integration disabled by configuration",
            }

        if not self.subscriber:
            return {
                "enabled": True,
                "status": "error",
                "message": "Redis subscriber not initialized",
                "initialization_error": self.initialization_error,
            }

        # Get subscriber status
        subscription_status = self.subscriber.get_subscription_status()
        processing_history = self.subscriber.get_processing_history()

        return {
            "enabled": True,
            "status": (
                "connected"
                if subscription_status.get("connection_status", {}).get("is_connected", False)
                else "disconnected"
            ),
            "redis_url": self.redis_url,
            "subscription_status": subscription_status,
            "processing_history": processing_history,
            "calendar_sync_callback_configured": self.calendar_sync_callback is not None,
        }

    def get_subscription_statistics(self) -> Dict[str, Any]:
        """
        Get detailed subscription statistics.

        Returns:
            Dict[str, Any]: Subscription statistics
        """
        if not self.enabled or not self.subscriber:
            return {"enabled": False, "statistics": {}}

        status = self.subscriber.get_subscription_status()
        history = self.subscriber.get_processing_history()

        return {
            "enabled": True,
            "subscription_active": status.get("subscription_active", False),
            "active_channels": status.get("active_channels", []),
            "statistics": {
                "subscription_stats": status.get("subscription_stats", {}),
                "message_processing": status.get("message_processing", {}),
                "latest_status": history.get("latest_status"),
                "status_history_count": len(history.get("status_history", [])),
            },
        }

    def test_redis_integration(self) -> Dict[str, Any]:
        """
        Test Redis integration functionality.

        Returns:
            Dict[str, Any]: Test results
        """
        if not self.enabled:
            return {
                "enabled": False,
                "test_results": {"overall_success": False, "message": "Redis integration disabled"},
            }

        if not self.subscriber:
            return {
                "enabled": True,
                "test_results": {
                    "overall_success": False,
                    "message": "Redis subscriber not initialized",
                },
            }

        try:
            logger.info("🧪 Testing Redis integration...")

            test_results = self.subscriber.test_subscription()

            if test_results["overall_success"]:
                logger.info("✅ Redis integration test successful")
            else:
                logger.warning("⚠️ Redis integration test failed")
                for error in test_results.get("errors", []):
                    logger.warning(f"   - {error}")

            return {"enabled": True, "test_results": test_results}

        except Exception as e:
            logger.error(f"❌ Redis integration test error: {e}")
            return {
                "enabled": True,
                "test_results": {"overall_success": False, "errors": [f"Test exception: {e}"]},
            }

    def restart_subscription(self) -> bool:
        """
        Restart Redis subscription (useful for recovery).

        Returns:
            bool: True if restart successful
        """
        if not self.enabled:
            return False

        logger.info("🔄 Restarting Redis subscription...")

        # Stop current subscription
        self.stop_redis_subscription()

        # Reinitialize subscriber if needed
        if not self.subscriber:
            self._initialize_redis_subscriber()

        # Start subscription again
        return self.start_redis_subscription()

    def close(self) -> None:
        """Close Redis service gracefully."""
        if self.subscriber:
            logger.info("🔌 Closing Redis service")
            self.subscriber.close()
            self.subscriber = None


# Convenience functions for external use
def create_calendar_redis_service(
    redis_url: str = None,
    enabled: bool = None,
    calendar_sync_callback: Callable[[List[Dict]], bool] = None,
) -> CalendarServiceRedisService:
    """
    Create Redis service for calendar with optional configuration.

    Args:
        redis_url: Custom Redis URL (optional)
        enabled: Whether Redis integration is enabled (optional)
        calendar_sync_callback: Function to call for calendar synchronization

    Returns:
        CalendarServiceRedisService: Configured Redis service
    """
    return CalendarServiceRedisService(redis_url, enabled, calendar_sync_callback)


def integrate_with_flask_app(app, calendar_sync_callback: Callable[[List[Dict]], bool] = None):
    """
    Integrate Redis service with Flask application.

    Args:
        app: Flask application instance
        calendar_sync_callback: Function to call for calendar synchronization

    Returns:
        CalendarServiceRedisService: Configured Redis service
    """
    # Create Redis service
    redis_service = create_calendar_redis_service(calendar_sync_callback=calendar_sync_callback)

    # Add to Flask app
    app.redis_service = redis_service

    # Add status endpoint
    @app.route("/redis-status", methods=["GET"])
    def redis_status():
        """Get Redis integration status."""
        from flask import jsonify

        status = redis_service.get_redis_status()
        return jsonify(status)

    @app.route("/redis-stats", methods=["GET"])
    def redis_stats():
        """Get Redis subscription statistics."""
        from flask import jsonify

        stats = redis_service.get_subscription_statistics()
        return jsonify(stats)

    @app.route("/redis-test", methods=["POST"])
    def redis_test():
        """Test Redis integration."""
        from flask import jsonify

        test_results = redis_service.test_redis_integration()
        return jsonify(test_results)

    # Start subscription if enabled
    if redis_service.enabled:
        redis_service.start_redis_subscription()

    logger.info("✅ Redis service integrated with Flask application")
    return redis_service


if __name__ == "__main__":
    # Test Redis service
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("🧪 Testing Redis service...")

    # Test calendar sync callback
    def test_calendar_sync(matches):
        logger.info(f"📅 Test calendar sync called with {len(matches)} matches")
        return True

    # Create service
    service = create_calendar_redis_service(calendar_sync_callback=test_calendar_sync)

    # Test integration
    test_results = service.test_redis_integration()

    if test_results.get("test_results", {}).get("overall_success"):
        logger.info("✅ Redis service test successful")
    else:
        logger.warning("⚠️ Redis service test failed (expected if Redis not available)")

    # Get status
    status = service.get_redis_status()
    logger.info(f"📊 Redis Service Status: {status['status']}")
    logger.info(f"   Enabled: {status['enabled']}")

    # Close service
    service.close()
