"""
Redis Integration Module for Calendar Service

Provides Redis pub/sub functionality for real-time match updates from the match processor.
Production-ready implementation with essential functionality and clean architecture.
"""

# Import Redis integration components
from .config import RedisConfig, get_redis_config, reload_redis_config
from .flask_integration import RedisFlaskIntegration, add_redis_to_calendar_app
from .subscriber import RedisSubscriber, create_redis_subscriber

__all__ = [
    # Configuration
    "RedisConfig",
    "get_redis_config",
    "reload_redis_config",
    # Subscriber
    "RedisSubscriber",
    "create_redis_subscriber",
    # Flask Integration
    "RedisFlaskIntegration",
    "add_redis_to_calendar_app",
]

__version__ = "1.0.0"
__author__ = "FOGIS System Architecture Team"
