#!/usr/bin/env python3
"""
Redis Subscriber for Calendar Service

This module provides Redis subscription capabilities for the FOGIS calendar service,
enabling real-time reception of match updates and processing status from other services.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis subscription for calendar service
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from .connection_manager import RedisSubscriptionManager, RedisSubscriptionConfig
from .message_handler import MatchUpdateHandler, ProcessingStatusHandler, MessageProcessingResult

logger = logging.getLogger(__name__)

@dataclass
class SubscriptionResult:
    """Result of a Redis subscription operation."""
    success: bool
    channel: str
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class CalendarServiceRedisSubscriber:
    """Redis subscriber for calendar service with comprehensive message handling."""
    
    def __init__(self, redis_config: RedisSubscriptionConfig = None, 
                 calendar_sync_callback: Callable[[List[Dict]], bool] = None):
        """
        Initialize Redis subscriber for calendar service.
        
        Args:
            redis_config: Redis subscription configuration
            calendar_sync_callback: Function to call for calendar synchronization
        """
        self.connection_manager = RedisSubscriptionManager(redis_config)
        self.match_handler = MatchUpdateHandler(calendar_sync_callback)
        self.status_handler = ProcessingStatusHandler()
        
        self.channels = {
            'match_updates': 'fogis:matches:updates',
            'processor_status': 'fogis:processor:status',
            'system_alerts': 'fogis:system:alerts'
        }
        
        self.subscription_stats = {
            'total_messages_received': 0,
            'successful_messages': 0,
            'failed_messages': 0,
            'subscription_start_time': None,
            'last_message_time': None,
            'active_subscriptions': set()
        }
        
        logger.info(f"📡 Calendar Service Redis Subscriber initialized")
        logger.info(f"   Channels: {list(self.channels.values())}")
        
        # Test connection on initialization
        if self.connection_manager.ensure_connection():
            logger.info("✅ Redis connection established for subscription")
        else:
            logger.warning("⚠️ Redis connection not available - subscription will be disabled")
    
    def start_subscription(self, channels: List[str] = None) -> bool:
        """
        Start Redis subscription for specified channels.
        
        Args:
            channels: List of channel names to subscribe to (defaults to all)
            
        Returns:
            bool: True if subscription started successfully
        """
        if channels is None:
            channels = list(self.channels.keys())
        
        try:
            logger.info(f"🚀 Starting Redis subscription for channels: {channels}")
            
            # Subscribe to each channel
            subscription_success = True
            for channel_name in channels:
                if channel_name in self.channels:
                    channel = self.channels[channel_name]
                    
                    success = self.connection_manager.subscribe_to_channel(
                        channel, self._handle_redis_message
                    )
                    
                    if success:
                        self.subscription_stats['active_subscriptions'].add(channel)
                        logger.info(f"✅ Subscribed to {channel}")
                    else:
                        logger.error(f"❌ Failed to subscribe to {channel}")
                        subscription_success = False
                else:
                    logger.warning(f"⚠️ Unknown channel: {channel_name}")
                    subscription_success = False
            
            if subscription_success:
                self.subscription_stats['subscription_start_time'] = datetime.now()
                logger.info("✅ Redis subscription started successfully")
                return True
            else:
                logger.error("❌ Failed to start Redis subscription")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscription: {e}")
            return False
    
    def _handle_redis_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming Redis message.
        
        Args:
            message: Redis message data
        """
        try:
            self.subscription_stats['total_messages_received'] += 1
            self.subscription_stats['last_message_time'] = datetime.now()
            
            message_type = message.get('type', 'unknown')
            message_id = message.get('message_id', 'unknown')
            
            logger.debug(f"📨 Received Redis message: {message_type} ({message_id})")
            
            # Route message to appropriate handler
            if message_type == 'match_updates':
                result = self.match_handler.handle_message(message)
            elif message_type == 'processing_status':
                result = self.match_handler.handle_message(message)
                # Also update status handler
                self.status_handler.handle_status_update(message)
            elif message_type == 'system_alert':
                result = self.match_handler.handle_message(message)
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
                result = MessageProcessingResult(
                    success=False,
                    message_type=message_type,
                    message_id=message_id,
                    error=f"Unknown message type: {message_type}"
                )
            
            # Update statistics
            if result.success:
                self.subscription_stats['successful_messages'] += 1
                logger.debug(f"✅ Message processed successfully in {result.processing_time_ms:.2f}ms")
            else:
                self.subscription_stats['failed_messages'] += 1
                logger.error(f"❌ Message processing failed: {result.error}")
                
        except Exception as e:
            self.subscription_stats['failed_messages'] += 1
            logger.error(f"❌ Error handling Redis message: {e}")
    
    def stop_subscription(self, channels: List[str] = None) -> bool:
        """
        Stop Redis subscription for specified channels.
        
        Args:
            channels: List of channel names to unsubscribe from (defaults to all)
            
        Returns:
            bool: True if unsubscription successful
        """
        if channels is None:
            channels = list(self.channels.keys())
        
        try:
            logger.info(f"🛑 Stopping Redis subscription for channels: {channels}")
            
            unsubscription_success = True
            for channel_name in channels:
                if channel_name in self.channels:
                    channel = self.channels[channel_name]
                    
                    success = self.connection_manager.unsubscribe_from_channel(channel)
                    
                    if success:
                        self.subscription_stats['active_subscriptions'].discard(channel)
                        logger.info(f"✅ Unsubscribed from {channel}")
                    else:
                        logger.error(f"❌ Failed to unsubscribe from {channel}")
                        unsubscription_success = False
                else:
                    logger.warning(f"⚠️ Unknown channel: {channel_name}")
            
            if unsubscription_success:
                logger.info("✅ Redis subscription stopped successfully")
                return True
            else:
                logger.error("❌ Failed to stop Redis subscription")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to stop Redis subscription: {e}")
            return False
    
    def get_subscription_status(self) -> Dict[str, Any]:
        """
        Get comprehensive subscription status and statistics.
        
        Returns:
            Dict[str, Any]: Subscription status information
        """
        connection_status = self.connection_manager.get_subscription_status()
        match_stats = self.match_handler.get_processing_stats()
        
        # Calculate uptime
        uptime_seconds = 0
        if self.subscription_stats['subscription_start_time']:
            uptime = datetime.now() - self.subscription_stats['subscription_start_time']
            uptime_seconds = uptime.total_seconds()
        
        return {
            "subscription_active": len(self.subscription_stats['active_subscriptions']) > 0,
            "active_channels": list(self.subscription_stats['active_subscriptions']),
            "subscription_stats": {
                **self.subscription_stats,
                "subscription_start_time": self.subscription_stats['subscription_start_time'].isoformat() if self.subscription_stats['subscription_start_time'] else None,
                "last_message_time": self.subscription_stats['last_message_time'].isoformat() if self.subscription_stats['last_message_time'] else None,
                "uptime_seconds": uptime_seconds,
                "active_subscriptions": list(self.subscription_stats['active_subscriptions'])
            },
            "connection_status": connection_status,
            "message_processing": match_stats,
            "channels_config": self.channels.copy()
        }
    
    def get_processing_history(self) -> Dict[str, Any]:
        """
        Get message processing history and status updates.
        
        Returns:
            Dict[str, Any]: Processing history information
        """
        return {
            "match_processing_stats": self.match_handler.get_processing_stats(),
            "status_history": self.status_handler.get_status_history(),
            "latest_status": self.status_handler.get_latest_status()
        }
    
    def test_subscription(self) -> Dict[str, Any]:
        """
        Test Redis subscription functionality.
        
        Returns:
            Dict[str, Any]: Test results
        """
        test_results = {
            "connection_test": False,
            "subscription_test": False,
            "message_handling_test": False,
            "overall_success": False,
            "errors": []
        }
        
        try:
            # Test connection
            if self.connection_manager.ensure_connection():
                test_results["connection_test"] = True
                logger.info("✅ Connection test passed")
            else:
                test_results["errors"].append("Redis connection failed")
                logger.error("❌ Connection test failed")
                return test_results
            
            # Test subscription (briefly)
            test_channel = self.channels['match_updates']
            if self.connection_manager.subscribe_to_channel(test_channel, lambda msg: None):
                test_results["subscription_test"] = True
                logger.info("✅ Subscription test passed")
                
                # Unsubscribe from test
                self.connection_manager.unsubscribe_from_channel(test_channel)
            else:
                test_results["errors"].append("Redis subscription failed")
                logger.error("❌ Subscription test failed")
                return test_results
            
            # Test message handling
            test_message = {
                'message_id': 'test-123',
                'timestamp': datetime.now().isoformat(),
                'source': 'test',
                'version': '1.0',
                'type': 'match_updates',
                'payload': {
                    'matches': [],
                    'metadata': {'has_changes': False}
                }
            }
            
            result = self.match_handler.handle_message(test_message)
            if result.success:
                test_results["message_handling_test"] = True
                logger.info("✅ Message handling test passed")
            else:
                test_results["errors"].append(f"Message handling failed: {result.error}")
                logger.error("❌ Message handling test failed")
                return test_results
            
            # All tests passed
            test_results["overall_success"] = True
            logger.info("✅ All subscription tests passed")
            
        except Exception as e:
            test_results["errors"].append(f"Test exception: {e}")
            logger.error(f"❌ Subscription test exception: {e}")
        
        return test_results
    
    def close(self) -> None:
        """Close Redis subscription gracefully."""
        logger.info("🔌 Closing Redis subscription")
        
        # Stop all subscriptions
        self.stop_subscription()
        
        # Close connection manager
        self.connection_manager.close()
        
        # Reset statistics
        self.subscription_stats['active_subscriptions'].clear()

# Convenience functions for external use
def create_calendar_redis_subscriber(redis_url: str = None, 
                                   calendar_sync_callback: Callable[[List[Dict]], bool] = None) -> CalendarServiceRedisSubscriber:
    """
    Create Redis subscriber for calendar service with optional configuration.
    
    Args:
        redis_url: Custom Redis URL (optional)
        calendar_sync_callback: Function to call for calendar synchronization
        
    Returns:
        CalendarServiceRedisSubscriber: Configured Redis subscriber
    """
    config = RedisSubscriptionConfig()
    if redis_url:
        config.url = redis_url
    
    return CalendarServiceRedisSubscriber(config, calendar_sync_callback)

def test_calendar_redis_subscription(redis_url: str = None) -> bool:
    """
    Test calendar Redis subscription functionality.
    
    Args:
        redis_url: Custom Redis URL (optional)
        
    Returns:
        bool: True if subscription test successful
    """
    subscriber = create_calendar_redis_subscriber(redis_url)
    test_results = subscriber.test_subscription()
    subscriber.close()
    return test_results["overall_success"]

if __name__ == "__main__":
    # Test Redis subscriber
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis subscriber...")
    
    # Test calendar sync callback
    def test_calendar_sync(matches):
        logger.info(f"📅 Test calendar sync called with {len(matches)} matches")
        return True
    
    # Create subscriber
    subscriber = create_calendar_redis_subscriber(calendar_sync_callback=test_calendar_sync)
    
    # Test subscription functionality
    test_results = subscriber.test_subscription()
    
    if test_results["overall_success"]:
        logger.info("✅ Redis subscriber test successful")
    else:
        logger.warning("⚠️ Redis subscriber test failed (expected if Redis not available)")
        for error in test_results["errors"]:
            logger.warning(f"   - {error}")
    
    # Get status
    status = subscriber.get_subscription_status()
    logger.info(f"📊 Subscription Status:")
    logger.info(f"   Connection Available: {status['connection_status']['redis_available']}")
    logger.info(f"   Is Connected: {status['connection_status']['is_connected']}")
    logger.info(f"   Configured Channels: {list(status['channels_config'].values())}")
    
    # Close subscriber
    subscriber.close()
