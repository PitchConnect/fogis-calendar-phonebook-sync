"""Tests for Redis integration in app.py."""

from unittest.mock import MagicMock, patch

import pytest


class TestInitializeGoogleServices:
    """Tests for initialize_google_services function."""

    @patch("os.path.exists")
    def test_initialize_google_services_no_token_file(self, mock_exists):
        """Test initialization when token file doesn't exist."""
        mock_exists.return_value = False

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False

    @patch("builtins.open", side_effect=Exception("File error"))
    @patch("os.path.exists")
    def test_initialize_google_services_exception(self, mock_exists, mock_file):
        """Test initialization handles exceptions gracefully."""
        mock_exists.return_value = True

        from app import initialize_google_services

        result = initialize_google_services()

        assert result is False


class TestCalendarSyncCallback:
    """Tests for calendar_sync_callback function."""

    @patch("app.calendar_service", None)
    def test_calendar_sync_callback_no_service(self):
        """Test callback when calendar service is not initialized."""
        from app import calendar_sync_callback

        result = calendar_sync_callback([{"matchid": "123"}])

        assert result is False

    @patch("app.calendar_service", MagicMock())
    def test_calendar_sync_callback_empty_matches(self):
        """Test callback with empty matches list."""
        from app import calendar_sync_callback

        result = calendar_sync_callback([])

        assert result is True

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", return_value=True)
    def test_calendar_sync_callback_success(self, mock_sync):
        """Test successful calendar sync callback."""
        matches = [
            {
                "matchid": "123",
                "lag1namn": "Team A",
                "lag2namn": "Team B",
            }
        ]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is True

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", return_value=False)
    def test_calendar_sync_callback_sync_failure(self, mock_sync):
        """Test callback when sync_calendar fails."""
        matches = [{"matchid": "123"}]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is False

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", side_effect=Exception("Sync error"))
    def test_calendar_sync_callback_match_exception(self, mock_sync):
        """Test callback handles exceptions during match processing."""
        matches = [{"matchid": "123"}]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is False

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", side_effect=[True, False])
    def test_calendar_sync_callback_partial_success(self, mock_sync):
        """Test callback with partial success."""
        matches = [{"matchid": "123"}, {"matchid": "456"}]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is True

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", side_effect=[True, True, False, True])
    def test_calendar_sync_callback_multiple_matches(self, mock_sync):
        """Test callback with multiple matches to cover iteration logic."""
        matches = [
            {"matchid": "1"},
            {"matchid": "2"},
            {"matchid": "3"},
            {"matchid": "4"},
        ]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is True
        assert mock_sync.call_count == 4

    @patch("app.calendar_service", MagicMock())
    @patch("fogis_calendar_sync.sync_calendar", return_value=False)
    def test_calendar_sync_callback_all_failures(self, mock_sync):
        """Test callback when all matches fail."""
        matches = [{"matchid": "1"}, {"matchid": "2"}]

        from app import calendar_sync_callback

        result = calendar_sync_callback(matches)

        assert result is False
