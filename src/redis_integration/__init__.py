"""
Redis Integration Module for Calendar Service

This module provides Redis pub/sub subscription integration for the FOGIS calendar service,
enabling real-time reception of match updates from the match processor.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis pub/sub subscription integration for calendar service
"""

from .subscriber import CalendarServiceRedisSubscriber
from .message_handler import MatchUpdateHandler, ProcessingStatusHandler
from .connection_manager import RedisConnectionManager
from .redis_service import CalendarServiceRedisService

__all__ = [
    'CalendarServiceRedisSubscriber',
    'MatchUpdateHandler',
    'ProcessingStatusHandler', 
    'RedisConnectionManager',
    'CalendarServiceRedisService'
]

__version__ = "1.0.0"
__author__ = "FOGIS System Architecture Team"
