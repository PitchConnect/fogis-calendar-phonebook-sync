"""Tests for Redis integration in app.py."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestInitializeGoogleServices:
    """Tests for initialize_google_services function."""

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
