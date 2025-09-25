#!/usr/bin/env python3
"""
Service Wrapper for Redis Integration Test Compatibility

Provides wrapper classes that match the API expected by legacy integration tests.
This maintains backward compatibility while using the current Redis integration implementation.
"""

import logging
from typing import Callable, Dict, List, Optional

from flask import Flask

from .config import RedisConfig, get_redis_config
from .connection_manager import ConnectionManager
from .flask_integration import RedisFlaskIntegration
from .subscriber import RedisSubscriber, create_redis_subscriber

logger = logging.getLogger(__name__)


# Alias for test compatibility
RedisSubscriptionConfig = RedisConfig


class CalendarServiceRedisService:
    """
    Wrapper class for Redis service functionality to maintain test compatibility.

    This class provides the interface expected by integration tests while using
    the current Redis integration implementation under the hood.
    """

    def __init__(
        self, enabled: bool = True, calendar_sync_callback: Callable = None, redis_url: str = None
    ):
        """Initialize calendar service Redis integration."""
        self.enabled = enabled
        self.calendar_sync_callback = calendar_sync_callback
        self.subscriber = None
        self.config = None

        if redis_url:
            # Create custom config with provided URL
            self.config = RedisConfig(url=redis_url, enabled=enabled)
        else:
            # Use default config but override enabled flag
            self.config = get_redis_config()
            self.config.enabled = enabled

        if enabled and calendar_sync_callback:
            self.subscriber = create_redis_subscriber(self.config, calendar_sync_callback)
            # Add connection_manager attribute for test compatibility
            if self.subscriber:
                self.subscriber.connection_manager = ConnectionManager(self.config)

    def start_redis_subscription(self) -> bool:
        """Start Redis subscription."""
        if not self.enabled or not self.subscriber:
            return False

        try:
            self.subscriber.start_subscription()
            return True
        except Exception as e:
            logger.error(f"Failed to start Redis subscription: {e}")
            return False

    def stop_redis_subscription(self) -> bool:
        """Stop Redis subscription."""
        if not self.subscriber:
            return True  # No-op if no subscriber

        try:
            self.subscriber.stop_subscription()
            return True
        except Exception as e:
            logger.error(f"Failed to stop Redis subscription: {e}")
            return False

    def get_redis_status(self) -> Dict:
        """Get Redis service status."""
        if not self.enabled:
            return {"enabled": False, "status": "disabled", "connection": "not_applicable"}

        if not self.subscriber:
            return {"enabled": True, "status": "not_initialized", "connection": "not_connected"}

        try:
            subscriber_status = self.subscriber.get_status()
            return {
                "enabled": True,
                "status": "active" if subscriber_status.get("connected", False) else "inactive",
                "connection": (
                    "connected" if subscriber_status.get("connected", False) else "disconnected"
                ),
                "subscriber_status": subscriber_status,
            }
        except Exception as e:
            return {"enabled": True, "status": "error", "connection": "error", "error": str(e)}

    def get_statistics(self) -> Dict:
        """Get Redis service statistics."""
        if not self.enabled or not self.subscriber:
            return {"enabled": self.enabled, "messages_processed": 0, "errors": 0, "uptime": 0}

        try:
            stats = self.subscriber.get_statistics()
            return {
                "enabled": True,
                "messages_processed": stats.get("messages_processed", 0),
                "errors": stats.get("errors", 0),
                "uptime": stats.get("uptime", 0),
                "last_message": stats.get("last_message_time"),
                "channels": stats.get("subscribed_channels", []),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis statistics: {e}")
            return {
                "enabled": True,
                "messages_processed": 0,
                "errors": 1,
                "uptime": 0,
                "error": str(e),
            }

    def test_redis_integration(self) -> Dict:
        """Test Redis integration functionality."""
        if not self.enabled:
            return {"success": False, "reason": "Redis integration disabled", "tests": []}

        tests = []
        overall_success = True

        # Test 1: Configuration
        try:
            config_test = {
                "name": "configuration",
                "success": self.config is not None,
                "details": f"Config loaded: {self.config.url if self.config else 'None'}",
            }
            tests.append(config_test)
            if not config_test["success"]:
                overall_success = False
        except Exception as e:
            tests.append(
                {"name": "configuration", "success": False, "details": f"Configuration error: {e}"}
            )
            overall_success = False

        # Test 2: Subscriber creation
        try:
            subscriber_test = {
                "name": "subscriber",
                "success": self.subscriber is not None,
                "details": f"Subscriber created: {type(self.subscriber).__name__ if self.subscriber else 'None'}",
            }
            tests.append(subscriber_test)
            if not subscriber_test["success"]:
                overall_success = False
        except Exception as e:
            tests.append(
                {"name": "subscriber", "success": False, "details": f"Subscriber error: {e}"}
            )
            overall_success = False

        # Test 3: Connection (if subscriber exists)
        if self.subscriber:
            try:
                status = self.subscriber.get_status()
                connection_test = {
                    "name": "connection",
                    "success": status.get("connected", False),
                    "details": f"Connection status: {status}",
                }
                tests.append(connection_test)
                if not connection_test["success"]:
                    overall_success = False
            except Exception as e:
                tests.append(
                    {"name": "connection", "success": False, "details": f"Connection error: {e}"}
                )
                overall_success = False

        return {
            "success": overall_success,
            "tests": tests,
            "summary": f"{len([t for t in tests if t['success']])}/{len(tests)} tests passed",
        }

    def set_calendar_sync_callback(self, callback: Callable):
        """Update the calendar sync callback."""
        self.calendar_sync_callback = callback
        if self.subscriber:
            self.subscriber.calendar_sync_callback = callback


class CalendarRedisFlaskIntegration:
    """
    Wrapper class for Flask Redis integration to maintain test compatibility.

    This class provides the interface expected by integration tests while using
    the current RedisFlaskIntegration implementation under the hood.
    """

    def __init__(self, app: Flask = None, calendar_sync_callback: Callable = None):
        """Initialize Flask Redis integration wrapper."""
        self.app = app
        self.calendar_sync_callback = calendar_sync_callback
        self.redis_service = None
        self._flask_integration = None

        if app:
            self.init_app(app, calendar_sync_callback)

    def init_app(self, app: Flask, calendar_sync_callback: Callable = None):
        """Initialize Flask app with Redis integration."""
        self.app = app
        self.calendar_sync_callback = calendar_sync_callback or self.calendar_sync_callback

        # Create underlying Flask integration
        self._flask_integration = RedisFlaskIntegration(app, self.calendar_sync_callback)

        # Create service wrapper for compatibility
        self.redis_service = CalendarServiceRedisService(
            enabled=True, calendar_sync_callback=self.calendar_sync_callback
        )

        # Add redis_service to app for test compatibility
        app.redis_service = self.redis_service

    def set_calendar_sync_callback(self, callback: Callable):
        """Update the calendar sync callback."""
        self.calendar_sync_callback = callback
        if self.redis_service:
            self.redis_service.set_calendar_sync_callback(callback)
        if self._flask_integration:
            self._flask_integration.calendar_sync_callback = callback
