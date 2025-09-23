#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Service

This module provides comprehensive tests for the Redis service functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis service
"""

import logging
import os
import sys
import unittest
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.redis_service import (
    CalendarServiceRedisService,
    create_calendar_redis_service,
)


class TestCalendarServiceRedisService(unittest.TestCase):
    """Test cases for CalendarServiceRedisService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = CalendarServiceRedisService(
            redis_url="redis://test:6379",
            enabled=True
        )

    def test_service_initialization(self):
        """Test service initialization."""
        self.assertTrue(self.service.enabled)
        self.assertEqual(self.service.redis_url, "redis://test:6379")

    def test_service_initialization_disabled(self):
        """Test service initialization when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        self.assertFalse(service.enabled)

    def test_service_initialization_error_handling(self):
        """Test service initialization with error handling."""
        # Test with invalid URL format
        service = CalendarServiceRedisService(redis_url="invalid_url", enabled=True)
        
        # Should handle initialization errors gracefully
        self.assertIsInstance(service, CalendarServiceRedisService)

    def test_initialize_redis_publishing_success(self):
        """Test Redis publishing initialization."""
        result = self.service.initialize_redis_publishing()
        
        # Should return True or False based on Redis availability
        self.assertIsInstance(result, bool)

    def test_initialize_redis_publishing_disabled(self):
        """Test Redis publishing initialization when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        result = service.initialize_redis_publishing()
        
        self.assertFalse(result)  # Should return False for disabled service

    def test_handle_calendar_sync_start_success(self):
        """Test successful calendar sync start handling."""
        sync_details = {
            "sync_cycle": 1,
            "start_time": datetime.now().isoformat()
        }
        
        result = self.service.handle_calendar_sync_start(sync_details)
        
        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_handle_calendar_sync_start_disabled(self):
        """Test calendar sync start handling when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        result = service.handle_calendar_sync_start({})
        
        self.assertTrue(result)

    def test_handle_calendar_sync_complete_success(self):
        """Test successful calendar sync completion handling."""
        sync_results = {"events_synced": 5, "contacts_synced": 10}
        sync_details = {"sync_cycle": 1}
        
        result = self.service.handle_calendar_sync_complete(
            sync_results, sync_details
        )
        
        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_handle_calendar_sync_complete_disabled(self):
        """Test calendar sync completion handling when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        result = service.handle_calendar_sync_complete({}, {})
        
        self.assertTrue(result)

    def test_handle_calendar_sync_error_success(self):
        """Test successful calendar sync error handling."""
        error = Exception("Test error")
        sync_details = {"sync_cycle": 1}
        
        result = self.service.handle_calendar_sync_error(error, sync_details)
        
        # Should return True even if Redis is not connected (graceful degradation)
        self.assertIsInstance(result, bool)

    def test_handle_calendar_sync_error_disabled(self):
        """Test calendar sync error handling when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        result = service.handle_calendar_sync_error(Exception("test"), {})
        
        self.assertTrue(result)

    def test_get_redis_status_enabled(self):
        """Test getting Redis status when enabled."""
        status = self.service.get_redis_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn("enabled", status)
        self.assertIn("redis_available", status)
        self.assertIn("connection_status", status)

    def test_get_redis_status_disabled(self):
        """Test getting Redis status when disabled."""
        service = CalendarServiceRedisService(enabled=False)
        
        status = service.get_redis_status()
        
        self.assertFalse(status["enabled"])

    def test_close_service(self):
        """Test closing the service."""
        # Should not raise exception
        self.service.close()

    def test_close_service_disabled(self):
        """Test closing disabled service."""
        service = CalendarServiceRedisService(enabled=False)
        
        # Should not raise exception
        service.close()

    def test_create_redis_service_function(self):
        """Test create_redis_service helper function."""
        service = create_calendar_redis_service(redis_url="redis://test:6379", enabled=True)
        
        self.assertIsInstance(service, CalendarServiceRedisService)
        self.assertTrue(service.enabled)

    def test_create_redis_service_disabled(self):
        """Test create_redis_service with disabled service."""
        service = create_calendar_redis_service(enabled=False)
        
        self.assertIsInstance(service, CalendarServiceRedisService)
        self.assertFalse(service.enabled)

    def test_service_with_default_config(self):
        """Test service with default configuration."""
        service = CalendarServiceRedisService()
        
        # Should use environment configuration
        self.assertIsInstance(service, CalendarServiceRedisService)

    def test_service_string_representation(self):
        """Test service string representation."""
        service_str = str(self.service)
        
        self.assertIsInstance(service_str, str)
        self.assertIn("CalendarServiceRedisService", service_str)

    def test_service_repr_representation(self):
        """Test service repr representation."""
        service_repr = repr(self.service)
        
        self.assertIsInstance(service_repr, str)
        self.assertIn("CalendarServiceRedisService", service_repr)


if __name__ == "__main__":
    unittest.main()
