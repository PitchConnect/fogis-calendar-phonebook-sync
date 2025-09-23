# flake8: noqa: E402#!/usr/bin/env python3
"""
Tests for Calendar Service Redis Message Handler

This module provides comprehensive tests for the Redis message handling functionality
in the FOGIS calendar service.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Tests for calendar service Redis message handler
"""

import logging
import os

# Import modules to test
import sys
import unittest
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from redis_integration.message_handler import (
    MatchUpdateHandler,
    MessageProcessingResult,
    ProcessingStatusHandler,
    create_match_update_handler,
    create_processing_status_handler,
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMatchUpdateHandler(unittest.TestCase):
    """Test cases for MatchUpdateHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.calendar_sync_calls = []
        self.calendar_sync_results = []

        def mock_calendar_sync(matches):
            """Mock calendar sync function."""
            self.calendar_sync_calls.append(matches)
            # Return the next result or True by default
            if self.calendar_sync_results:
                return self.calendar_sync_results.pop(0)
            return True

        self.mock_calendar_sync = mock_calendar_sync
        self.handler = MatchUpdateHandler(self.mock_calendar_sync)

    def test_handler_initialization(self):
        """Test message handler initialization."""
        self.assertIsNotNone(self.handler)
        self.assertEqual(self.handler.calendar_sync_callback, self.mock_calendar_sync)
        self.assertIsNotNone(self.handler.processing_stats)
        self.assertEqual(self.handler.processing_stats["total_messages"], 0)

    def test_handler_initialization_without_callback(self):
        """Test message handler initialization without callback."""
        handler = MatchUpdateHandler()
        self.assertIsNotNone(handler)
        self.assertIsNone(handler.calendar_sync_callback)

    def test_valid_match_update_message(self):
        """Test handling valid match update message."""
        message = {
            "message_id": "test-123",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [
                    {"matchid": 123456, "hemmalag": "Team A", "bortalag": "Team B"},
                    {"matchid": 789012, "hemmalag": "Team C", "bortalag": "Team D"},
                ],
                "metadata": {
                    "has_changes": True,
                    "change_summary": {"new_matches": 2, "updated_matches": 0},
                },
            },
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.message_type, "match_updates")
        self.assertEqual(result.message_id, "test-123")
        self.assertEqual(result.matches_processed, 2)
        self.assertIsNone(result.error)
        self.assertGreater(result.processing_time_ms, 0)

        # Check calendar sync was called
        self.assertEqual(len(self.calendar_sync_calls), 1)
        self.assertEqual(len(self.calendar_sync_calls[0]), 2)

        # Check statistics
        stats = self.handler.get_processing_stats()
        self.assertEqual(stats["total_messages"], 1)
        self.assertEqual(stats["successful_messages"], 1)
        self.assertEqual(stats["failed_messages"], 0)

    def test_match_update_no_changes(self):
        """Test handling match update message with no changes."""
        message = {
            "message_id": "test-456",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"matchid": 123456, "hemmalag": "Team A", "bortalag": "Team B"}],
                "metadata": {
                    "has_changes": False,
                    "change_summary": {"new_matches": 0, "updated_matches": 0},
                },
            },
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.matches_processed, 1)

        # Calendar sync should not be called for no changes
        self.assertEqual(len(self.calendar_sync_calls), 0)

    def test_calendar_sync_failure(self):
        """Test handling when calendar sync fails."""
        # Set up calendar sync to fail
        self.calendar_sync_results = [False]

        message = {
            "message_id": "test-789",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"matchid": 123456}],
                "metadata": {"has_changes": True},
            },
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertFalse(result.success)
        self.assertEqual(result.matches_processed, 0)
        self.assertIn("Calendar synchronization failed", result.error)

        # Check statistics
        stats = self.handler.get_processing_stats()
        self.assertEqual(stats["failed_messages"], 1)

    def test_calendar_sync_exception(self):
        """Test handling when calendar sync raises exception."""

        def failing_callback(matches):
            raise Exception("Calendar sync error")

        handler = MatchUpdateHandler(failing_callback)

        message = {
            "message_id": "test-error",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"matchid": 123456}],
                "metadata": {"has_changes": True},
            },
        }

        result = handler.handle_message(message)

        # Check result
        self.assertFalse(result.success)
        self.assertIn("Calendar sync callback failed", result.error)

    def test_processing_status_message(self):
        """Test handling processing status message."""
        message = {
            "message_id": "status-123",
            "timestamp": datetime.now().isoformat(),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "processing_status",
            "payload": {
                "status": "completed",
                "cycle_number": 42,
                "matches_processed": 10,
                "processing_duration_ms": 5000,
            },
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.message_type, "processing_status")
        self.assertEqual(result.matches_processed, 10)

    def test_system_alert_message(self):
        """Test handling system alert message."""
        message = {
            "message_id": "alert-123",
            "timestamp": datetime.now().isoformat(),
            "source": "system",
            "version": "1.0",
            "type": "system_alert",
            "payload": {
                "alert_type": "error",
                "severity": "high",
                "message": "Test system alert",
            },
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.message_type, "system_alert")

    def test_invalid_message_missing_fields(self):
        """Test handling message with missing required fields."""
        message = {
            "message_id": "invalid-123",
            # Missing timestamp, source, version, type, payload
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertFalse(result.success)
        self.assertIn("Missing required field", result.error)

    def test_invalid_message_unsupported_version(self):
        """Test handling message with unsupported version."""
        message = {
            "message_id": "version-test",
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "version": "2.0",  # Unsupported version
            "type": "match_updates",
            "payload": {},
        }

        result = self.handler.handle_message(message)

        # Should still process but log warning
        # (Current implementation processes unsupported versions with warning)
        self.assertIsNotNone(result)

    def test_unknown_message_type(self):
        """Test handling message with unknown type."""
        message = {
            "message_id": "unknown-123",
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "version": "1.0",
            "type": "unknown_type",
            "payload": {},
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertFalse(result.success)
        self.assertIn("Unknown message type", result.error)

    def test_message_processing_exception(self):
        """Test handling when message processing raises exception."""
        # Create malformed message that will cause exception
        message = {
            "message_id": "exception-test",
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "version": "1.0",
            "type": "match_updates",
            "payload": None,  # This will cause exception when accessing payload
        }

        result = self.handler.handle_message(message)

        # Check result
        self.assertFalse(result.success)
        self.assertIn("Failed to process match updates", result.error)

    def test_processing_statistics(self):
        """Test processing statistics tracking."""
        # Process multiple messages
        messages = [
            {
                "message_id": f"test-{i}",
                "timestamp": datetime.now().isoformat(),
                "source": "test",
                "version": "1.0",
                "type": "match_updates",
                "payload": {
                    "matches": [{"matchid": i}],
                    "metadata": {"has_changes": True},
                },
            }
            for i in range(5)
        ]

        # Process all messages
        for message in messages:
            self.handler.handle_message(message)

        # Check statistics
        stats = self.handler.get_processing_stats()
        self.assertEqual(stats["total_messages"], 5)
        self.assertEqual(stats["successful_messages"], 5)
        self.assertEqual(stats["failed_messages"], 0)
        self.assertIsNotNone(stats["last_processed"])
        self.assertIsNone(stats["last_error"])

    def test_reset_statistics(self):
        """Test resetting processing statistics."""
        # Process a message
        message = {
            "message_id": "test-reset",
            "timestamp": datetime.now().isoformat(),
            "source": "test",
            "version": "1.0",
            "type": "match_updates",
            "payload": {"matches": [], "metadata": {"has_changes": False}},
        }

        self.handler.handle_message(message)

        # Check statistics before reset
        stats = self.handler.get_processing_stats()
        self.assertEqual(stats["total_messages"], 1)

        # Reset statistics
        self.handler.reset_stats()

        # Check statistics after reset
        stats = self.handler.get_processing_stats()
        self.assertEqual(stats["total_messages"], 0)
        self.assertEqual(stats["successful_messages"], 0)
        self.assertEqual(stats["failed_messages"], 0)
        self.assertIsNone(stats["last_processed"])
        self.assertIsNone(stats["last_error"])


class TestProcessingStatusHandler(unittest.TestCase):
    """Test cases for ProcessingStatusHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = ProcessingStatusHandler()

    def test_handler_initialization(self):
        """Test status handler initialization."""
        self.assertIsNotNone(self.handler)
        self.assertEqual(len(self.handler.status_history), 0)
        self.assertEqual(self.handler.max_history, 100)

    def test_handle_status_update(self):
        """Test handling status update."""
        message = {
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "status": "completed",
                "cycle_number": 42,
                "matches_processed": 10,
                "processing_duration_ms": 5000,
            },
        }

        success = self.handler.handle_status_update(message)

        self.assertTrue(success)
        self.assertEqual(len(self.handler.status_history), 1)

        latest = self.handler.get_latest_status()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["status"], "completed")
        self.assertEqual(latest["cycle_number"], 42)
        self.assertEqual(latest["matches_processed"], 10)

    def test_status_history_limit(self):
        """Test status history size limit."""
        # Add more than max_history entries
        for i in range(150):
            message = {
                "timestamp": datetime.now().isoformat(),
                "payload": {"status": f"status-{i}", "cycle_number": i},
            }
            self.handler.handle_status_update(message)

        # Should be limited to max_history
        self.assertEqual(len(self.handler.status_history), 100)

        # Should contain the latest entries
        latest = self.handler.get_latest_status()
        self.assertEqual(latest["status"], "status-149")

    def test_get_status_history(self):
        """Test getting status history."""
        # Add some status updates
        for i in range(5):
            message = {
                "timestamp": datetime.now().isoformat(),
                "payload": {"status": f"status-{i}", "cycle_number": i},
            }
            self.handler.handle_status_update(message)

        history = self.handler.get_status_history()
        self.assertEqual(len(history), 5)

        # Check that it's a copy (not the original)
        history.clear()
        self.assertEqual(len(self.handler.status_history), 5)

    def test_get_latest_status_empty(self):
        """Test getting latest status when history is empty."""
        latest = self.handler.get_latest_status()
        self.assertIsNone(latest)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""

    def test_create_match_update_handler(self):
        """Test creating match update handler with convenience function."""

        def test_callback(matches):
            return True

        handler = create_match_update_handler(test_callback)

        self.assertIsNotNone(handler)
        self.assertEqual(handler.calendar_sync_callback, test_callback)

    def test_create_match_update_handler_no_callback(self):
        """Test creating match update handler without callback."""
        handler = create_match_update_handler()

        self.assertIsNotNone(handler)
        self.assertIsNone(handler.calendar_sync_callback)

    def test_create_processing_status_handler(self):
        """Test creating processing status handler."""
        handler = create_processing_status_handler()

        self.assertIsNotNone(handler)
        self.assertEqual(len(handler.status_history), 0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
