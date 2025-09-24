#!/usr/bin/env python3
"""
Simplified Flask Integration for Redis Calendar Service

Consolidates Flask endpoints and integration logic.
Reduces complexity from 660 lines to ~100 lines.
"""

import logging
from datetime import datetime
from typing import Callable, Dict, List

from flask import Flask, jsonify, request

from .config import get_redis_config
from .subscriber_simple import create_redis_subscriber

logger = logging.getLogger(__name__)


class RedisFlaskIntegration:
    """Simplified Flask integration for Redis subscription."""

    def __init__(self, app: Flask = None, calendar_sync_callback: Callable = None):
        """Initialize Flask integration."""
        self.app = app
        self.calendar_sync_callback = calendar_sync_callback
        self.subscriber = None

        if app:
            self.init_app(app, calendar_sync_callback)

    def init_app(self, app: Flask, calendar_sync_callback: Callable = None):
        """Initialize Flask app with Redis integration."""
        self.app = app
        self.calendar_sync_callback = calendar_sync_callback or self.calendar_sync_callback

        # Create Redis subscriber
        config = get_redis_config()
        self.subscriber = create_redis_subscriber(config, self.calendar_sync_callback)

        # Start subscription if enabled
        if config.enabled:
            self.subscriber.start_subscription()

        # Register endpoints
        self._register_endpoints()

        # Add to app for reference
        app.redis_integration = self

        logger.info("✅ Redis Flask integration initialized")

    def _register_endpoints(self):
        """Register Redis endpoints."""

        @self.app.route("/redis-status", methods=["GET"])
        def redis_status():
            """Get Redis integration status."""
            try:
                status = self.subscriber.get_status() if self.subscriber else {"enabled": False}
                return (
                    jsonify(
                        {
                            "success": True,
                            "timestamp": datetime.now().isoformat(),
                            "redis_status": status,
                        }
                    ),
                    200,
                )
            except Exception as e:
                return (
                    jsonify(
                        {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
                    ),
                    500,
                )

        @self.app.route("/redis-stats", methods=["GET"])
        def redis_stats():
            """Get Redis subscription statistics."""
            try:
                stats = {
                    "subscription_active": self.subscriber.running if self.subscriber else False,
                    "channels": list(get_redis_config().channels.values()),
                    "timestamp": datetime.now().isoformat(),
                }
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/redis-test", methods=["POST"])
        def redis_test():
            """Test Redis integration."""
            try:
                if not self.subscriber:
                    return (
                        jsonify({"success": False, "error": "Redis subscriber not initialized"}),
                        500,
                    )

                status = self.subscriber.get_status()
                return jsonify({"success": True, "test_results": status}), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/manual-sync", methods=["POST"])
        def manual_sync():
            """Manual calendar sync endpoint."""
            try:
                data = request.get_json()
                if not data or "matches" not in data:
                    return (
                        jsonify({"success": False, "error": "Missing 'matches' in request data"}),
                        400,
                    )

                matches = data["matches"]

                if self.calendar_sync_callback:
                    success = self.calendar_sync_callback(matches)
                    return jsonify(
                        {
                            "success": success,
                            "matches_processed": len(matches),
                            "timestamp": datetime.now().isoformat(),
                        }
                    ), (200 if success else 500)
                else:
                    return (
                        jsonify(
                            {"success": False, "error": "No calendar sync callback configured"}
                        ),
                        500,
                    )

            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/redis-restart", methods=["POST"])
        def redis_restart():
            """Restart Redis subscription."""
            try:
                if self.subscriber:
                    self.subscriber.stop_subscription()

                    # Recreate subscriber
                    config = get_redis_config()
                    self.subscriber = create_redis_subscriber(config, self.calendar_sync_callback)

                    if config.enabled:
                        success = self.subscriber.start_subscription()
                        return jsonify(
                            {
                                "success": success,
                                "message": (
                                    "Redis subscription restarted"
                                    if success
                                    else "Failed to restart subscription"
                                ),
                                "timestamp": datetime.now().isoformat(),
                            }
                        ), (200 if success else 500)
                    else:
                        return jsonify({"success": False, "message": "Redis is disabled"}), 400
                else:
                    return (
                        jsonify({"success": False, "error": "Redis subscriber not initialized"}),
                        500,
                    )
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/redis-config", methods=["GET"])
        def redis_config():
            """Get Redis configuration."""
            try:
                config = get_redis_config()
                return (
                    jsonify(
                        {
                            "success": True,
                            "config": {
                                "url": config.url,
                                "enabled": config.enabled,
                                "timeout": config.timeout,
                                "channels": config.channels,
                            },
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                    200,
                )
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    def close(self):
        """Close Redis integration."""
        if self.subscriber:
            self.subscriber.stop_subscription()


def add_redis_to_calendar_app(app: Flask, calendar_sync_function: Callable[[List[Dict]], bool]):
    """Add Redis integration to existing calendar Flask application."""
    logger.info("🔗 Adding Redis integration to calendar Flask app...")

    integration = RedisFlaskIntegration(app, calendar_sync_function)

    logger.info("✅ Redis integration added to calendar Flask application")
    logger.info("📡 Available Redis endpoints:")
    logger.info("   GET  /redis-status  - Redis integration status")
    logger.info("   GET  /redis-stats   - Redis subscription statistics")
    logger.info("   POST /redis-test    - Test Redis integration")
    logger.info("   POST /redis-restart - Restart Redis subscription")
    logger.info("   POST /manual-sync   - Manual calendar sync (fallback)")
    logger.info("   GET  /redis-config  - Redis configuration")

    return integration
