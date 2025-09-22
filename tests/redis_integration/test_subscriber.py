#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Subscriber

This module provides comprehensive tests for the Redis subscriber functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis subscriber
"""

import unittest
import logging
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from redis_integration.subscriber import CalendarServiceRedisSubscriber, create_calendar_redis_subscriber
from redis_integration.connection_manager import RedisSubscriptionConfig

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCalendarServiceRedisSubscriber(unittest.TestCase):
    """Test cases for CalendarServiceRedisSubscriber."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = RedisSubscriptionConfig(
            url="redis://localhost:6379",
            socket_connect_timeout=1,
            socket_timeout=1,
            max_retries=1,
            retry_delay=0.1
        )
        
        self.calendar_sync_calls = []
        
        def mock_calendar_sync(matches):
            """Mock calendar sync function."""
            self.calendar_sync_calls.append(matches)
            return True
        
        self.mock_calendar_sync = mock_calendar_sync
    
    def test_subscriber_initialization(self):
        """Test Redis subscriber initialization."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        self.assertIsNotNone(subscriber)
        self.assertIsNotNone(subscriber.connection_manager)
        self.assertIsNotNone(subscriber.match_handler)
        self.assertIsNotNone(subscriber.status_handler)
        self.assertEqual(len(subscriber.channels), 3)
        
        # Check channels configuration
        expected_channels = {
            'match_updates': 'fogis:matches:updates',
            'processor_status': 'fogis:processor:status',
            'system_alerts': 'fogis:system:alerts'
        }
        self.assertEqual(subscriber.channels, expected_channels)
    
    def test_subscriber_initialization_without_callback(self):
        """Test Redis subscriber initialization without calendar sync callback."""
        subscriber = CalendarServiceRedisSubscriber(redis_config=self.test_config)
        
        self.assertIsNotNone(subscriber)
        self.assertIsNone(subscriber.match_handler.calendar_sync_callback)
    
    @patch('redis_integration.connection_manager.REDIS_AVAILABLE', False)
    def test_subscriber_without_redis(self):
        """Test Redis subscriber when Redis is not available."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Should still initialize but connection will fail
        self.assertIsNotNone(subscriber)
        
        # Start subscription should fail gracefully
        success = subscriber.start_subscription()
        self.assertFalse(success)
    
    @patch('redis_integration.connection_manager.redis')
    def test_subscription_start_success(self, mock_redis):
        """Test successful subscription start."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client
        
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Mock successful subscription
        subscriber.connection_manager.subscribe_to_channel = Mock(return_value=True)
        
        success = subscriber.start_subscription()
        self.assertTrue(success)
        
        # Check that all channels were subscribed
        self.assertEqual(subscriber.connection_manager.subscribe_to_channel.call_count, 3)
    
    @patch('redis_integration.connection_manager.redis')
    def test_subscription_start_partial_failure(self, mock_redis):
        """Test subscription start with partial failures."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client
        
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Mock partial subscription failure
        def mock_subscribe(channel, handler):
            return channel != 'fogis:processor:status'  # Fail on one channel
        
        subscriber.connection_manager.subscribe_to_channel = Mock(side_effect=mock_subscribe)
        
        success = subscriber.start_subscription()
        self.assertFalse(success)
    
    def test_message_handling_match_updates(self):
        """Test handling of match update messages."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Create test message
        test_message = {
            'message_id': 'test-123',
            'timestamp': datetime.now().isoformat(),
            'source': 'match-list-processor',
            'version': '1.0',
            'type': 'match_updates',
            'payload': {
                'matches': [
                    {'matchid': 123456, 'hemmalag': 'Team A', 'bortalag': 'Team B'}
                ],
                'metadata': {
                    'has_changes': True,
                    'change_summary': {'new_matches': 1}
                }
            }
        }
        
        # Handle message
        subscriber._handle_redis_message(test_message)
        
        # Check that calendar sync was called
        self.assertEqual(len(self.calendar_sync_calls), 1)
        self.assertEqual(len(self.calendar_sync_calls[0]), 1)
        self.assertEqual(self.calendar_sync_calls[0][0]['matchid'], 123456)
        
        # Check statistics
        stats = subscriber.subscription_stats
        self.assertEqual(stats['total_messages_received'], 1)
        self.assertEqual(stats['successful_messages'], 1)
        self.assertEqual(stats['failed_messages'], 0)
    
    def test_message_handling_processing_status(self):
        """Test handling of processing status messages."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Create test message
        test_message = {
            'message_id': 'status-123',
            'timestamp': datetime.now().isoformat(),
            'source': 'match-list-processor',
            'version': '1.0',
            'type': 'processing_status',
            'payload': {
                'status': 'completed',
                'cycle_number': 42,
                'matches_processed': 10
            }
        }
        
        # Handle message
        subscriber._handle_redis_message(test_message)
        
        # Check that status was recorded
        latest_status = subscriber.status_handler.get_latest_status()
        self.assertIsNotNone(latest_status)
        self.assertEqual(latest_status['status'], 'completed')
        self.assertEqual(latest_status['cycle_number'], 42)
        self.assertEqual(latest_status['matches_processed'], 10)
    
    def test_message_handling_system_alert(self):
        """Test handling of system alert messages."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Create test message
        test_message = {
            'message_id': 'alert-123',
            'timestamp': datetime.now().isoformat(),
            'source': 'system',
            'version': '1.0',
            'type': 'system_alert',
            'payload': {
                'alert_type': 'error',
                'severity': 'high',
                'message': 'Test system alert'
            }
        }
        
        # Handle message
        subscriber._handle_redis_message(test_message)
        
        # Check statistics
        stats = subscriber.subscription_stats
        self.assertEqual(stats['total_messages_received'], 1)
        self.assertEqual(stats['successful_messages'], 1)
    
    def test_message_handling_unknown_type(self):
        """Test handling of unknown message types."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Create test message with unknown type
        test_message = {
            'message_id': 'unknown-123',
            'timestamp': datetime.now().isoformat(),
            'source': 'test',
            'version': '1.0',
            'type': 'unknown_type',
            'payload': {}
        }
        
        # Handle message
        subscriber._handle_redis_message(test_message)
        
        # Check statistics - should be marked as failed
        stats = subscriber.subscription_stats
        self.assertEqual(stats['total_messages_received'], 1)
        self.assertEqual(stats['failed_messages'], 1)
    
    def test_subscription_status(self):
        """Test getting subscription status."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        status = subscriber.get_subscription_status()
        
        # Check status structure
        self.assertIn('subscription_active', status)
        self.assertIn('active_channels', status)
        self.assertIn('subscription_stats', status)
        self.assertIn('connection_status', status)
        self.assertIn('message_processing', status)
        self.assertIn('channels_config', status)
        
        # Check channels configuration
        self.assertEqual(len(status['channels_config']), 3)
        self.assertIn('match_updates', status['channels_config'])
        self.assertIn('processor_status', status['channels_config'])
        self.assertIn('system_alerts', status['channels_config'])
    
    def test_processing_history(self):
        """Test getting processing history."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        history = subscriber.get_processing_history()
        
        # Check history structure
        self.assertIn('match_processing_stats', history)
        self.assertIn('status_history', history)
        self.assertIn('latest_status', history)
        
        # Initially should be empty
        self.assertEqual(len(history['status_history']), 0)
        self.assertIsNone(history['latest_status'])
    
    @patch('redis_integration.connection_manager.redis')
    def test_subscription_test(self, mock_redis):
        """Test subscription testing functionality."""
        # Mock Redis client
        mock_client = Mock()
        mock_pubsub = Mock()
        mock_client.ping.return_value = True
        mock_client.pubsub.return_value = mock_pubsub
        mock_redis.from_url.return_value = mock_client
        
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Mock successful operations
        subscriber.connection_manager.ensure_connection = Mock(return_value=True)
        subscriber.connection_manager.subscribe_to_channel = Mock(return_value=True)
        subscriber.connection_manager.unsubscribe_from_channel = Mock(return_value=True)
        
        test_results = subscriber.test_subscription()
        
        self.assertTrue(test_results['overall_success'])
        self.assertTrue(test_results['connection_test'])
        self.assertTrue(test_results['subscription_test'])
        self.assertTrue(test_results['message_handling_test'])
        self.assertEqual(len(test_results['errors']), 0)
    
    def test_subscription_stop(self):
        """Test stopping subscription."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Mock successful unsubscription
        subscriber.connection_manager.unsubscribe_from_channel = Mock(return_value=True)
        
        success = subscriber.stop_subscription()
        self.assertTrue(success)
        
        # Check that all channels were unsubscribed
        self.assertEqual(subscriber.connection_manager.unsubscribe_from_channel.call_count, 3)
    
    def test_subscriber_close(self):
        """Test closing subscriber."""
        subscriber = CalendarServiceRedisSubscriber(
            redis_config=self.test_config,
            calendar_sync_callback=self.mock_calendar_sync
        )
        
        # Mock methods
        subscriber.stop_subscription = Mock(return_value=True)
        subscriber.connection_manager.close = Mock()
        
        # Close subscriber
        subscriber.close()
        
        # Check that cleanup was called
        subscriber.stop_subscription.assert_called_once()
        subscriber.connection_manager.close.assert_called_once()
        self.assertEqual(len(subscriber.subscription_stats['active_subscriptions']), 0)

class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""
    
    def test_create_calendar_redis_subscriber(self):
        """Test creating Redis subscriber with convenience function."""
        def test_callback(matches):
            return True
        
        subscriber = create_calendar_redis_subscriber(
            redis_url="redis://test:6379",
            calendar_sync_callback=test_callback
        )
        
        self.assertIsNotNone(subscriber)
        self.assertEqual(subscriber.connection_manager.config.url, "redis://test:6379")
        self.assertEqual(subscriber.match_handler.calendar_sync_callback, test_callback)
    
    def test_create_calendar_redis_subscriber_defaults(self):
        """Test creating Redis subscriber with default configuration."""
        subscriber = create_calendar_redis_subscriber()
        
        self.assertIsNotNone(subscriber)
        self.assertIsNotNone(subscriber.connection_manager.config.url)

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
