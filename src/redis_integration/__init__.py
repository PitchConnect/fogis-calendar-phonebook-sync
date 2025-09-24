"""
Simplified Redis Integration Module for Calendar Service

Provides essential Redis pub/sub functionality for real-time match updates.
Simplified from 7 modules to 3 core modules.
"""

# Import simplified components
from .config import RedisConfig, get_redis_config, reload_redis_config
from .flask_integration_simple import RedisFlaskIntegration, add_redis_to_calendar_app
from .subscriber_simple import RedisSubscriber, create_redis_subscriber

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

__version__ = "2.0.0"
__author__ = "FOGIS System Architecture Team"
