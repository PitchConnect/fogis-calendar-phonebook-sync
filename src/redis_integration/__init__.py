"""
Redis Integration Module for Calendar Service

Provides Redis pub/sub functionality for real-time match updates from the match processor.
Enhanced Schema v2.0 support with logo service integration and intelligent sync priority.
"""

from . import connection_manager

# Import Redis integration components
from .config import RedisConfig, get_redis_config, reload_redis_config
from .flask_integration import RedisFlaskIntegration, add_redis_to_calendar_app
from .logo_service import LogoServiceClient, create_logo_service_client
from .service_wrapper import (
    CalendarRedisFlaskIntegration,
    CalendarServiceRedisService,
    CalendarServiceRedisSubscriber,
    RedisSubscriptionConfig,
)
from .subscriber import RedisSubscriber, create_redis_subscriber

__all__ = [
    # Configuration
    "RedisConfig",
    "get_redis_config",
    "reload_redis_config",
    # Subscriber
    "RedisSubscriber",
    "create_redis_subscriber",
    # Logo Service
    "LogoServiceClient",
    "create_logo_service_client",
    # Flask Integration
    "RedisFlaskIntegration",
    "add_redis_to_calendar_app",
    # Test Compatibility Wrappers
    "CalendarServiceRedisService",
    "CalendarServiceRedisSubscriber",
    "CalendarRedisFlaskIntegration",
    "RedisSubscriptionConfig",
]

__version__ = "2.0.0"
__author__ = "FOGIS System Architecture Team"
