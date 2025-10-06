#!/usr/bin/env python3
"""
Unit tests for Enhanced Schema v2.0 Redis integration.

Tests schema version detection, logo service integration, and intelligent sync priority.
"""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

from src.redis_integration.config import RedisConfig
from src.redis_integration.logo_service import LogoServiceClient
from src.redis_integration.subscriber import RedisSubscriber


class TestEnhancedSchemaV2(unittest.TestCase):
    """Test Enhanced Schema v2.0 functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RedisConfig(
            url="redis://test:6379",
            enabled=True,
            schema_version="2.0",
            logo_service_url="http://test-logo-service:5002",
        )
        self.mock_callback = Mock(return_value=True)
        self.mock_logo_client = Mock(spec=LogoServiceClient)

    def test_schema_version_detection_v2(self):
        """Test detection of Enhanced Schema v2.0 messages."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Create v2.0 message
        message_data = {
            "schema_version": "2.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"match_id": 123, "teams": {"home": {}, "away": {}}}],
                "metadata": {"has_changes": True},
            },
        }

        message = {"data": json.dumps(message_data)}

        # Handle message
        subscriber._handle_message(message)

        # Verify v2.0 counter incremented
        self.assertEqual(subscriber.schema_v2_messages, 1)
        self.assertEqual(subscriber.schema_v1_messages, 0)

    def test_schema_version_detection_v1(self):
        """Test detection of legacy schema v1.0 messages."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Create v1.0 message
        message_data = {
            "schema_version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"matchid": 123, "hemmalag": "Team A", "bortalag": "Team B"}],
                "metadata": {"has_changes": True},
            },
        }

        message = {"data": json.dumps(message_data)}

        # Handle message
        subscriber._handle_message(message)

        # Verify v1.0 counter incremented
        self.assertEqual(subscriber.schema_v1_messages, 1)
        self.assertEqual(subscriber.schema_v2_messages, 0)

    def test_high_priority_change_detection(self):
        """Test detection of high-priority changes."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Test with high-priority changes
        changes = [
            {"field": "avsparkstid", "priority": "high", "category": "time_change"},
            {"field": "anlaggning", "priority": "medium", "category": "venue_change"},
        ]

        result = subscriber._has_high_priority_changes(changes)
        self.assertTrue(result)

        # Test with only medium-priority changes
        changes = [{"field": "referee", "priority": "medium", "category": "referee_update"}]

        result = subscriber._has_high_priority_changes(changes)
        self.assertFalse(result)

    def test_logo_enrichment(self):
        """Test match enrichment with team logos."""
        # Mock logo service to return a path
        self.mock_logo_client.generate_combined_logo = Mock(return_value="/tmp/logo_123_456.png")

        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Create matches with Organization IDs
        matches = [
            {
                "match_id": 123,
                "teams": {
                    "home": {"name": "Team A", "organization_id": 123, "logo_id": 123},
                    "away": {"name": "Team B", "organization_id": 456, "logo_id": 456},
                },
            }
        ]

        # Enrich matches
        enriched = subscriber._enrich_matches_with_logos(matches)

        # Verify logo path added
        self.assertEqual(len(enriched), 1)
        self.assertIn("logo_path", enriched[0])
        self.assertEqual(enriched[0]["logo_path"], "/tmp/logo_123_456.png")

        # Verify logo service was called
        self.mock_logo_client.generate_combined_logo.assert_called_once_with(123, 456)

    def test_enhanced_schema_callback_format(self):
        """Test that Enhanced Schema v2.0 passes enriched data to callback."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Create v2.0 message
        message_data = {
            "schema_version": "2.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"match_id": 123, "teams": {"home": {}, "away": {}}}],
                "detailed_changes": [{"field": "time", "priority": "high"}],
                "metadata": {"has_changes": True},
            },
        }

        message = {"data": json.dumps(message_data)}

        # Handle message
        subscriber._handle_message(message)

        # Verify callback was called with enriched data
        self.mock_callback.assert_called_once()
        call_args = self.mock_callback.call_args[0][0]

        # Check enriched data structure
        self.assertIsInstance(call_args, dict)
        self.assertIn("matches", call_args)
        self.assertIn("schema_version", call_args)
        self.assertIn("detailed_changes", call_args)
        self.assertIn("high_priority", call_args)
        self.assertEqual(call_args["schema_version"], "2.0")
        self.assertTrue(call_args["high_priority"])

    def test_backward_compatibility_with_legacy_callback(self):  # noqa: D202
        """Test backward compatibility with callbacks expecting simple list."""

        # Create callback that only accepts list (old format)
        def legacy_callback(matches):
            if isinstance(matches, dict):
                raise TypeError("Expected list, got dict")
            return True

        subscriber = RedisSubscriber(self.config, legacy_callback, self.mock_logo_client)

        # Create v1.0 message
        message_data = {
            "schema_version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": [{"matchid": 123}],
                "metadata": {"has_changes": True},
            },
        }

        message = {"data": json.dumps(message_data)}

        # Should not raise exception
        subscriber._handle_message(message)

    def test_statistics_include_schema_versions(self):
        """Test that statistics include schema version breakdown."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Process some messages
        subscriber.schema_v2_messages = 5
        subscriber.schema_v1_messages = 3
        subscriber.schema_unknown_messages = 1

        stats = subscriber.get_statistics()

        # Verify schema stats included
        self.assertIn("schema_version_stats", stats)
        self.assertEqual(stats["schema_version_stats"]["v2_messages"], 5)
        self.assertEqual(stats["schema_version_stats"]["v1_messages"], 3)
        self.assertEqual(stats["schema_version_stats"]["unknown_messages"], 1)
        self.assertEqual(stats["schema_version_stats"]["preferred_schema"], "2.0")

    def test_logo_service_statistics(self):
        """Test that statistics include logo service information."""
        self.mock_logo_client.get_cache_size = Mock(return_value=10)

        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        stats = subscriber.get_statistics()

        # Verify logo service stats included
        self.assertIn("logo_service", stats)
        self.assertTrue(stats["logo_service"]["enabled"])
        self.assertEqual(stats["logo_service"]["cache_size"], 10)

    def test_missing_organization_ids(self):
        """Test handling of matches without Organization IDs."""
        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        # Create matches without Organization IDs
        matches = [{"match_id": 123, "teams": {"home": {"name": "Team A"}, "away": {}}}]

        # Should not raise exception
        enriched = subscriber._enrich_matches_with_logos(matches)

        # Verify no logo path added
        self.assertEqual(len(enriched), 1)
        self.assertNotIn("logo_path", enriched[0])

    def test_logo_service_failure_graceful_degradation(self):
        """Test graceful degradation when logo service fails."""
        # Mock logo service to return None (failure)
        self.mock_logo_client.generate_combined_logo = Mock(return_value=None)

        subscriber = RedisSubscriber(self.config, self.mock_callback, self.mock_logo_client)

        matches = [
            {
                "match_id": 123,
                "teams": {
                    "home": {"organization_id": 123},
                    "away": {"organization_id": 456},
                },
            }
        ]

        # Should not raise exception
        enriched = subscriber._enrich_matches_with_logos(matches)

        # Verify no logo path added when service fails
        self.assertEqual(len(enriched), 1)
        self.assertNotIn("logo_path", enriched[0])


class TestLogoServiceClient(unittest.TestCase):
    """Test LogoServiceClient functionality."""

    @patch("src.redis_integration.logo_service.requests")
    def test_logo_generation_success(self, mock_requests):
        """Test successful logo generation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_requests.post.return_value = mock_response

        client = LogoServiceClient("http://test:5002")
        result = client.generate_combined_logo(123, 456)

        # Verify logo was saved
        self.assertIsNotNone(result)
        self.assertIn("combined_logo_123_456.png", result)

    @patch("src.redis_integration.logo_service.requests")
    def test_logo_generation_caching(self, mock_requests):
        """Test that logos are cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_requests.post.return_value = mock_response

        client = LogoServiceClient("http://test:5002")

        # Generate logo twice
        result1 = client.generate_combined_logo(123, 456)
        result2 = client.generate_combined_logo(123, 456)

        # Verify same result
        self.assertEqual(result1, result2)

        # Verify API called only once (cached second time)
        self.assertEqual(mock_requests.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
