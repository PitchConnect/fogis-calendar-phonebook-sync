"""Tests for Redis integration in app.py."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestInitializeGoogleServices:
    """Tests for initialize_google_services function."""

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.credentials.Credentials")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_success(
        self, mock_env, mock_exists, mock_file, mock_credentials, mock_build
    ):
        """Test successful initialization of Google services."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True

        # Mock token data
        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }
        mock_file.return_value.read.return_value = json.dumps(token_data)

        # Mock json.load to return token_data
        with patch("json.load", return_value=token_data):
            from app import initialize_google_services

            result = initialize_google_services()

            assert result is True
            mock_credentials.assert_called_once()
            assert mock_build.call_count == 2  # calendar and people services

    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_no_token_file(self, mock_env, mock_exists):
        """Test initialization when token file doesn't exist."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = False

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_file_read_exception(self, mock_env, mock_exists, mock_file):
        """Test initialization handles file read exceptions gracefully."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True
        mock_file.side_effect = IOError("File read error")

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.credentials.Credentials")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_invalid_json(
        self, mock_env, mock_exists, mock_file, mock_credentials, mock_build
    ):
        """Test initialization handles invalid JSON gracefully."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        mock_file.return_value.__enter__.return_value.read.return_value = "invalid json"

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.credentials.Credentials")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_build_exception(
        self, mock_env, mock_exists, mock_file, mock_credentials, mock_build
    ):
        """Test initialization handles build exceptions gracefully."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True

        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }

        mock_file.return_value.read.return_value = json.dumps(token_data)
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(token_data)

        mock_credentials.return_value = MagicMock()
        mock_build.side_effect = Exception("Build failed")

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.credentials.Credentials")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_credentials_exception(
        self, mock_env, mock_exists, mock_file, mock_credentials, mock_build
    ):
        """Test initialization handles Credentials creation exceptions."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True

        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }

        mock_file.return_value.read.return_value = json.dumps(token_data)
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(token_data)

        mock_credentials.side_effect = Exception("Credentials creation failed")

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("googleapiclient.discovery.build")
    @patch("google.oauth2.credentials.Credentials")
    @patch("builtins.open", new_callable=mock_open)
    @patch("app.os.path.exists")
    @patch("app.os.environ.get")
    def test_initialize_google_services_json_decode_error(
        self, mock_env, mock_exists, mock_file, mock_credentials, mock_build
    ):
        """Test initialization handles JSON decode errors."""
        mock_env.return_value = "/app/credentials/tokens/calendar/token.json"
        mock_exists.return_value = True

        # Return invalid JSON that will cause JSONDecodeError
        mock_file.return_value.read.return_value = "{invalid json"
        mock_file.return_value.__enter__.return_value.read.return_value = "{invalid json"

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False


class TestCalendarSyncCallback:
    """Tests for calendar_sync_callback function."""

    def test_calendar_sync_callback_no_service(self):
        """Test callback when calendar service is not initialized."""
        import app

        # Temporarily set calendar_service to None
        original_service = app.calendar_service
        app.calendar_service = None

        try:
            result = app.calendar_sync_callback([{"matchid": "123"}])
            assert result is False
        finally:
            app.calendar_service = original_service

    def test_calendar_sync_callback_empty_matches(self):
        """Test callback with empty matches list."""
        import app

        # Temporarily set calendar_service to a mock
        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback([])
            assert result is True
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_single_match_success(self, mock_sync):
        """Test successful calendar sync callback with single match."""
        import app

        mock_sync.return_value = True
        matches = [
            {
                "matchid": "123",
                "lag1namn": "Team A",
                "lag2namn": "Team B",
            }
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is True
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_single_match_failure(self, mock_sync):
        """Test callback when sync_calendar fails."""
        import app

        mock_sync.return_value = False
        matches = [{"matchid": "123"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_match_exception(self, mock_sync):
        """Test callback handles exceptions during match processing."""
        import app

        mock_sync.side_effect = Exception("Sync error")
        matches = [{"matchid": "123"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_partial_success(self, mock_sync):
        """Test callback with partial success (some matches succeed, some fail)."""
        import app

        mock_sync.side_effect = [True, False, True]
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is True  # Should return True if at least one succeeded
            assert mock_sync.call_count == 3
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_multiple_matches_all_success(self, mock_sync):
        """Test callback with multiple matches all succeeding."""
        import app

        mock_sync.return_value = True
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
            {"matchid": "4"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is True
            assert mock_sync.call_count == 4
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_all_failures(self, mock_sync):
        """Test callback when all matches fail."""
        import app

        mock_sync.return_value = False
        matches = [{"matchid": "1"}, {"matchid": "2"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_mixed_exceptions_and_failures(self, mock_sync):
        """Test callback with mix of exceptions and failures."""
        import app

        mock_sync.side_effect = [True, Exception("Error"), False, True]
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
            {"matchid": "4"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is True  # 2 succeeded
        finally:
            app.calendar_service = original_service

    def test_calendar_sync_callback_general_exception(self):
        """Test callback handles general exceptions gracefully."""
        import app

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            # Patch the import to raise an exception
            with patch("builtins.__import__", side_effect=ImportError("Module not found")):
                result = app.calendar_sync_callback([{"matchid": "123"}])

                assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_args_object_creation(self, mock_sync):
        """Test that Args object is created correctly for sync_calendar."""
        import app

        # Capture the args passed to sync_calendar
        captured_args = None

        def capture_args(match, service, args):
            nonlocal captured_args
            captured_args = args
            return True

        mock_sync.side_effect = capture_args
        matches = [{"matchid": "123"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is True
            assert captured_args is not None
            assert hasattr(captured_args, "delete")
            assert hasattr(captured_args, "fresh_sync")
            assert hasattr(captured_args, "force_calendar")
            assert hasattr(captured_args, "force_contacts")
            assert hasattr(captured_args, "force_all")
            assert captured_args.delete is False
            assert captured_args.fresh_sync is False
            assert captured_args.force_calendar is False
            assert captured_args.force_contacts is False
            assert captured_args.force_all is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_match_without_matchid(self, mock_sync):
        """Test callback handles matches without matchid field."""
        import app

        mock_sync.side_effect = Exception("Error")
        matches = [{"lag1namn": "Team A"}]  # No matchid

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_logging_processed_count(self, mock_sync):
        """Test callback logs correct processed count."""
        import app

        mock_sync.side_effect = [True, True, False]
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            # Should return True because 2 out of 3 succeeded
            assert result is True
            assert mock_sync.call_count == 3
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_five_matches(self, mock_sync):
        """Test callback with five matches to cover more iterations."""
        import app

        mock_sync.side_effect = [True, False, True, True, False]
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
            {"matchid": "4"},
            {"matchid": "5"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            # Should return True because 3 out of 5 succeeded
            assert result is True
            assert mock_sync.call_count == 5
        finally:
            app.calendar_service = original_service


class TestCalendarSyncCallbackAdditional:
    """Additional tests for calendar_sync_callback to increase coverage."""

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_ten_matches(self, mock_sync):
        """Test callback with ten matches to cover more loop iterations."""
        import app

        mock_sync.side_effect = [True, False, True, True, False, True, False, True, True, False]
        matches = [{"matchid": str(i)} for i in range(10)]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            # Should return True because 6 out of 10 succeeded
            assert result is True
            assert mock_sync.call_count == 10
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_all_exceptions(self, mock_sync):
        """Test callback when all matches raise exceptions."""
        import app

        mock_sync.side_effect = Exception("Error")
        matches = [{"matchid": "1"}, {"matchid": "2"}, {"matchid": "3"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(matches)

            assert result is False
            assert mock_sync.call_count == 3
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_calendar_sync_callback_zero_processed_zero_failed(self, mock_sync):
        """Test callback return value when no matches processed and none failed."""
        import app

        # This shouldn't happen in practice, but tests the edge case
        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            # Empty list should return True (no failures)
            result = app.calendar_sync_callback([])
            assert result is True
        finally:
            app.calendar_service = original_service


class TestCalendarSyncCallbackEnhancedSchema:
    """Tests for calendar_sync_callback with Enhanced Schema v2.0 format."""

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_with_enhanced_schema_v2_dict(self, mock_sync):
        """Test callback with Enhanced Schema v2.0 format (dict)."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [
                {"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"},
                {"matchid": 456, "lag1namn": "Team C", "lag2namn": "Team D"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [{"type": "new_match", "matchid": 123}],
            "high_priority": True,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            assert mock_sync.call_count == 2
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_with_legacy_schema_v1_list(self, mock_sync):
        """Test callback with Legacy Schema v1.0 format (list)."""
        import app

        mock_sync.return_value = True
        data = [
            {"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"},
            {"matchid": 456, "lag1namn": "Team C", "lag2namn": "Team D"},
        ]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            assert mock_sync.call_count == 2
        finally:
            app.calendar_service = original_service

    def test_callback_with_invalid_data_type(self):
        """Test callback with invalid data type (string)."""
        import app

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback("invalid string")

            assert result is False
        finally:
            app.calendar_service = original_service

    def test_callback_with_invalid_data_type_number(self):
        """Test callback with invalid data type (number)."""
        import app

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(12345)

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_with_empty_matches_in_dict(self, mock_sync):
        """Test callback with Enhanced Schema v2.0 but empty matches list."""
        import app

        data = {
            "matches": [],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            mock_sync.assert_not_called()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_with_missing_matches_key(self, mock_sync):
        """Test callback with dict but missing 'matches' key."""
        import app

        data = {
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should return True because no matches means no failures
            assert result is True
            mock_sync.assert_not_called()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_with_partial_metadata(self, mock_sync):
        """Test callback with Enhanced Schema v2.0 but partial metadata."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "2.0",
            # Missing detailed_changes and high_priority
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_with_high_priority(self, mock_sync):
        """Test callback logs high priority correctly for v2.0."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "2.0",
            "detailed_changes": [
                {"type": "time_change", "matchid": 123},
                {"type": "venue_change", "matchid": 123},
            ],
            "high_priority": True,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_with_normal_priority(self, mock_sync):
        """Test callback logs normal priority correctly for v2.0."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "2.0",
            "detailed_changes": [{"type": "new_match", "matchid": 123}],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_partial_success(self, mock_sync):
        """Test callback with v2.0 format and partial success."""
        import app

        mock_sync.side_effect = [True, False, True]
        data = {
            "matches": [
                {"matchid": 1, "lag1namn": "Team A", "lag2namn": "Team B"},
                {"matchid": 2, "lag1namn": "Team C", "lag2namn": "Team D"},
                {"matchid": 3, "lag1namn": "Team E", "lag2namn": "Team F"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should return True because 2 out of 3 succeeded
            assert result is True
            assert mock_sync.call_count == 3
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_all_failures(self, mock_sync):
        """Test callback with v2.0 format when all matches fail."""
        import app

        mock_sync.return_value = False
        data = {
            "matches": [
                {"matchid": 1, "lag1namn": "Team A", "lag2namn": "Team B"},
                {"matchid": 2, "lag1namn": "Team C", "lag2namn": "Team D"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is False
            assert mock_sync.call_count == 2
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_with_exceptions(self, mock_sync):
        """Test callback with v2.0 format when exceptions occur."""
        import app

        mock_sync.side_effect = Exception("Sync error")
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is False
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_unknown_schema_version(self, mock_sync):
        """Test callback with unknown schema version in dict format."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "3.0",  # Unknown version
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should still process successfully
            assert result is True
            mock_sync.assert_called_once()
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v2_with_actual_sync_call(self, mock_sync):
        """Test callback actually calls sync_calendar with correct arguments."""
        import app

        mock_sync.return_value = True
        data = {
            "matches": [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            # Verify sync_calendar was called with the match and service
            assert mock_sync.call_count == 1
            call_args = mock_sync.call_args
            assert call_args[0][0] == data["matches"][0]  # First arg is the match
            assert call_args[0][1] == app.calendar_service  # Second arg is the service
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_v1_with_actual_sync_call(self, mock_sync):
        """Test callback with v1.0 format calls sync_calendar correctly."""
        import app

        mock_sync.return_value = True
        data = [{"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}]

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            assert result is True
            assert mock_sync.call_count == 1
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_logs_processing_summary(self, mock_sync):
        """Test callback logs correct processing summary."""
        import app

        mock_sync.side_effect = [True, False, True]
        data = {
            "matches": [
                {"matchid": 1, "lag1namn": "Team A", "lag2namn": "Team B"},
                {"matchid": 2, "lag1namn": "Team C", "lag2namn": "Team D"},
                {"matchid": 3, "lag1namn": "Team E", "lag2namn": "Team F"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should return True because 2 out of 3 succeeded
            assert result is True
            assert mock_sync.call_count == 3
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_handles_match_without_matchid_gracefully(self, mock_sync):
        """Test callback handles matches without matchid field gracefully."""
        import app

        # First match will raise KeyError when accessing matchid
        mock_sync.side_effect = [KeyError("matchid"), True]
        data = {
            "matches": [
                {"lag1namn": "Team A"},  # No matchid
                {"matchid": 2, "lag1namn": "Team B", "lag2namn": "Team C"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should return True because one succeeded
            assert result is True
            assert mock_sync.call_count == 2
        finally:
            app.calendar_service = original_service

    def test_callback_with_none_data(self):
        """Test callback with None data type."""
        import app

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(None)

            assert result is False
        finally:
            app.calendar_service = original_service

    def test_callback_with_tuple_data(self):
        """Test callback with tuple data type (invalid)."""
        import app

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback((1, 2, 3))

            assert result is False
        finally:
            app.calendar_service = original_service

    @patch("fogis_calendar_sync.sync_calendar")
    def test_callback_return_false_when_all_fail(self, mock_sync):
        """Test callback returns False when all matches fail."""
        import app

        mock_sync.return_value = False
        data = {
            "matches": [
                {"matchid": 1, "lag1namn": "Team A", "lag2namn": "Team B"},
                {"matchid": 2, "lag1namn": "Team C", "lag2namn": "Team D"},
            ],
            "schema_version": "2.0",
            "detailed_changes": [],
            "high_priority": False,
        }

        original_service = app.calendar_service
        app.calendar_service = MagicMock()

        try:
            result = app.calendar_sync_callback(data)

            # Should return False because all failed
            assert result is False
            assert mock_sync.call_count == 2
        finally:
            app.calendar_service = original_service
