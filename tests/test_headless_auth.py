"""Tests for headless_auth module."""

import json
import tempfile
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

import headless_auth


class TestHeadlessAuthManager:
    """Test cases for HeadlessAuthManager class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration data."""
        return {
            "CREDENTIALS_FILE": "test_credentials.json",
            "AUTH_SERVER_HOST": "localhost",
            "AUTH_SERVER_PORT": 8080,
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "user@example.com",
        }

    @pytest.fixture
    def mock_config_file(self, mock_config):
        """Mock config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mock_config, f)
            return f.name

    @pytest.fixture
    def auth_manager(self, mock_config_file):
        """Create HeadlessAuthManager instance with mocked dependencies."""
        with patch("headless_auth.TokenManager") as mock_token_manager, patch(
            "headless_auth.NotificationSender"
        ) as mock_notification_sender:

            manager = headless_auth.HeadlessAuthManager(mock_config_file)
            manager.token_manager = mock_token_manager.return_value
            manager.notification_sender = mock_notification_sender.return_value
            return manager

    def test_init_success(self, mock_config_file, mock_config):
        """Test successful initialization."""
        with patch("headless_auth.TokenManager") as mock_token_manager, patch(
            "headless_auth.NotificationSender"
        ) as mock_notification_sender:

            manager = headless_auth.HeadlessAuthManager(mock_config_file)

            assert manager.config_file == mock_config_file
            assert manager.config == mock_config
            assert manager.auth_server is None
            assert manager._monitoring is False
            assert manager._monitor_thread is None

            # Verify dependencies were created correctly
            mock_token_manager.assert_called_once_with(
                mock_config,
                credentials_file="test_credentials.json",
                token_file="token.json",
            )
            mock_notification_sender.assert_called_once_with(mock_config)

    def test_load_config_success(self, mock_config_file, mock_config):
        """Test successful config loading."""
        with patch("headless_auth.TokenManager"), patch("headless_auth.NotificationSender"):

            manager = headless_auth.HeadlessAuthManager(mock_config_file)
            assert manager.config == mock_config

    def test_load_config_file_not_found(self):
        """Test config loading with missing file."""
        with patch("headless_auth.TokenManager"), patch("headless_auth.NotificationSender"), patch(
            "headless_auth.logger"
        ) as mock_logger:

            manager = headless_auth.HeadlessAuthManager("nonexistent.json")
            assert manager.config == {}
            mock_logger.error.assert_called_once()

    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            invalid_file = f.name

        with patch("headless_auth.TokenManager"), patch("headless_auth.NotificationSender"), patch(
            "headless_auth.logger"
        ) as mock_logger:

            manager = headless_auth.HeadlessAuthManager(invalid_file)
            assert manager.config == {}
            mock_logger.error.assert_called_once()

    def test_get_valid_credentials_no_refresh_needed(self, auth_manager):
        """Test getting credentials when no refresh is needed."""
        mock_credentials = MagicMock()
        auth_manager.token_manager.check_token_expiration.return_value = (False, None)
        auth_manager.token_manager.get_credentials.return_value = mock_credentials

        with patch("headless_auth.logger") as mock_logger:
            result = auth_manager.get_valid_credentials()

            assert result == mock_credentials
            mock_logger.info.assert_called_with("Valid credentials obtained")

    def test_get_valid_credentials_refresh_needed_success(self, auth_manager):
        """Test getting credentials when refresh is needed and succeeds."""
        mock_credentials = MagicMock()
        expiry = datetime.now() + timedelta(days=1)
        auth_manager.token_manager.check_token_expiration.return_value = (True, expiry)
        auth_manager.token_manager.get_credentials.return_value = mock_credentials

        with patch.object(
            auth_manager, "_perform_headless_auth", return_value=True
        ) as mock_auth, patch("headless_auth.logger"):

            result = auth_manager.get_valid_credentials()

            assert result == mock_credentials
            mock_auth.assert_called_once()
            expected_expiry_info = (
                f"Current token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            mock_auth.assert_called_with(expected_expiry_info)

    def test_get_valid_credentials_refresh_needed_failure(self, auth_manager):
        """Test getting credentials when refresh is needed but fails."""
        expiry = datetime.now() + timedelta(days=1)
        auth_manager.token_manager.check_token_expiration.return_value = (True, expiry)

        with patch.object(auth_manager, "_perform_headless_auth", return_value=False), patch(
            "headless_auth.logger"
        ) as mock_logger:

            result = auth_manager.get_valid_credentials()

            assert result is None
            mock_logger.error.assert_called_with("Headless authentication failed")

    def test_get_valid_credentials_no_credentials_available(self, auth_manager):
        """Test getting credentials when none are available."""
        auth_manager.token_manager.check_token_expiration.return_value = (False, None)
        auth_manager.token_manager.get_credentials.return_value = None

        with patch("headless_auth.logger") as mock_logger:
            result = auth_manager.get_valid_credentials()

            assert result is None
            mock_logger.error.assert_called_with("No valid credentials available")

    def test_perform_headless_auth_success(self, auth_manager):
        """Test successful headless authentication."""
        mock_auth_server = MagicMock()
        mock_auth_server.start.return_value = "http://localhost:8080/auth"
        mock_auth_server.wait_for_auth.return_value = True

        with patch(
            "headless_auth.AuthServer", return_value=mock_auth_server
        ) as mock_auth_server_class, patch("headless_auth.logger") as mock_logger:

            auth_manager.notification_sender.send_auth_notification.return_value = True
            auth_manager.notification_sender.send_success_notification.return_value = True

            result = auth_manager._perform_headless_auth("test expiry info")

            assert result is True
            mock_auth_server_class.assert_called_once_with(
                auth_manager.config, auth_manager.token_manager
            )
            mock_auth_server.start.assert_called_once()
            mock_auth_server.wait_for_auth.assert_called_once_with(timeout=600)
            mock_auth_server.stop.assert_called_once()
            auth_manager.notification_sender.send_auth_notification.assert_called_once_with(
                "http://localhost:8080/auth", "test expiry info"
            )
            auth_manager.notification_sender.send_success_notification.assert_called_once()
            mock_logger.info.assert_any_call("Headless authentication completed successfully")

    def test_perform_headless_auth_timeout(self, auth_manager):
        """Test headless authentication timeout."""
        mock_auth_server = MagicMock()
        mock_auth_server.start.return_value = "http://localhost:8080/auth"
        mock_auth_server.wait_for_auth.return_value = False

        with patch("headless_auth.AuthServer", return_value=mock_auth_server), patch(
            "headless_auth.logger"
        ) as mock_logger:

            auth_manager.notification_sender.send_auth_notification.return_value = True

            result = auth_manager._perform_headless_auth()

            assert result is False
            mock_logger.error.assert_called_with("Headless authentication failed or timed out")

    def test_perform_headless_auth_exception(self, auth_manager):
        """Test headless authentication with exception."""
        with patch("headless_auth.AuthServer", side_effect=Exception("Test error")), patch(
            "headless_auth.logger"
        ) as mock_logger:

            result = auth_manager._perform_headless_auth()

            assert result is False
            mock_logger.exception.assert_called_once()

    def test_perform_headless_auth_cleanup_on_exception(self, auth_manager):
        """Test that auth server is cleaned up even when exception occurs."""
        mock_auth_server = MagicMock()
        mock_auth_server.start.side_effect = Exception("Test error")

        with patch("headless_auth.AuthServer", return_value=mock_auth_server), patch(
            "headless_auth.logger"
        ):

            auth_manager.auth_server = mock_auth_server  # Simulate server was created

            result = auth_manager._perform_headless_auth()

            assert result is False
            mock_auth_server.stop.assert_called_once()
            assert auth_manager.auth_server is None

    def test_start_monitoring_success(self, auth_manager):
        """Test starting monitoring successfully."""
        with patch("threading.Thread") as mock_thread, patch("headless_auth.logger") as mock_logger:

            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            auth_manager.start_monitoring()

            assert auth_manager._monitoring is True
            mock_thread.assert_called_once_with(target=auth_manager._monitor_loop)
            mock_thread_instance.start.assert_called_once()
            mock_logger.info.assert_called_with("Started background token monitoring")

    def test_start_monitoring_already_running(self, auth_manager):
        """Test starting monitoring when already running."""
        auth_manager._monitoring = True

        with patch("threading.Thread") as mock_thread, patch("headless_auth.logger") as mock_logger:

            auth_manager.start_monitoring()

            mock_thread.assert_not_called()
            mock_logger.warning.assert_called_with("Token monitoring already running")

    def test_stop_monitoring(self, auth_manager):
        """Test stopping monitoring."""
        mock_thread = MagicMock()
        auth_manager._monitoring = True
        auth_manager._monitor_thread = mock_thread

        with patch("headless_auth.logger") as mock_logger:
            auth_manager.stop_monitoring()

            assert auth_manager._monitoring is False
            mock_thread.join.assert_called_once_with(timeout=5)
            mock_logger.info.assert_called_with("Stopped background token monitoring")

    def test_get_token_status(self, auth_manager):
        """Test getting token status."""
        expected_status = {"valid": True, "expired": False}
        auth_manager.token_manager.get_token_info.return_value = expected_status

        result = auth_manager.get_token_status()

        assert result == expected_status
        auth_manager.token_manager.get_token_info.assert_called_once()

    def test_force_refresh(self, auth_manager):
        """Test forcing a token refresh."""
        with patch.object(
            auth_manager, "_perform_headless_auth", return_value=True
        ) as mock_auth, patch("headless_auth.logger") as mock_logger:

            result = auth_manager.force_refresh()

            assert result is True
            mock_logger.info.assert_called_with("Forcing token refresh")
            mock_auth.assert_called_once_with("Manual refresh requested")


class TestIntegrationFunctions:
    """Test cases for module-level integration functions."""

    def test_integrate_with_existing_auth_non_headless(self):
        """Test integration function with headless_mode=False."""
        config_dict = {"test": "config"}

        with patch("headless_auth.logger") as mock_logger:
            result = headless_auth.integrate_with_existing_auth(config_dict, headless_mode=False)

            assert result is None
            mock_logger.info.assert_called_with("Using standard (non-headless) authentication")

    def test_integrate_with_existing_auth_headless_success(self):
        """Test integration function with headless_mode=True and success."""
        config_dict = {"test": "config"}
        mock_credentials = MagicMock()

        with patch("headless_auth.HeadlessAuthManager") as mock_manager_class, patch(
            "headless_auth.logger"
        ) as mock_logger:

            mock_manager = MagicMock()
            mock_manager.get_valid_credentials.return_value = mock_credentials
            mock_manager_class.return_value = mock_manager

            result = headless_auth.integrate_with_existing_auth(config_dict, headless_mode=True)

            assert result == mock_credentials
            mock_logger.info.assert_called_with("Using headless authentication mode")
            mock_manager.get_valid_credentials.assert_called_once()
            mock_manager.start_monitoring.assert_called_once()

            # Check that manager was stored for cleanup
            assert hasattr(headless_auth.integrate_with_existing_auth, "_auth_managers")
            assert mock_manager in headless_auth.integrate_with_existing_auth._auth_managers

    def test_integrate_with_existing_auth_headless_failure(self):
        """Test integration function with headless_mode=True and failure."""
        config_dict = {"test": "config"}

        with patch("headless_auth.HeadlessAuthManager") as mock_manager_class, patch(
            "headless_auth.logger"
        ):

            mock_manager = MagicMock()
            mock_manager.get_valid_credentials.return_value = None
            mock_manager_class.return_value = mock_manager

            result = headless_auth.integrate_with_existing_auth(config_dict, headless_mode=True)

            assert result is None
            mock_manager.get_valid_credentials.assert_called_once()
            mock_manager.start_monitoring.assert_not_called()

    def test_cleanup_auth_managers(self):
        """Test cleanup function."""
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()

        # Set up managers list
        headless_auth.integrate_with_existing_auth._auth_managers = [
            mock_manager1,
            mock_manager2,
        ]

        headless_auth.cleanup_auth_managers()

        mock_manager1.stop_monitoring.assert_called_once()
        mock_manager2.stop_monitoring.assert_called_once()
        assert len(headless_auth.integrate_with_existing_auth._auth_managers) == 0

    def test_cleanup_auth_managers_no_managers(self):
        """Test cleanup function when no managers exist."""
        # Ensure no _auth_managers attribute exists
        if hasattr(headless_auth.integrate_with_existing_auth, "_auth_managers"):
            delattr(headless_auth.integrate_with_existing_auth, "_auth_managers")

        # Should not raise exception
        headless_auth.cleanup_auth_managers()


class TestMonitoringLoop:
    """Test cases for monitoring loop functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration data."""
        return {
            "CREDENTIALS_FILE": "test_credentials.json",
            "AUTH_SERVER_HOST": "localhost",
            "AUTH_SERVER_PORT": 8080,
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "user@example.com",
        }

    @pytest.fixture
    def mock_config_file(self, mock_config):
        """Mock config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(mock_config, f)
            return f.name

    @pytest.fixture
    def auth_manager_with_monitoring(self, mock_config_file):
        """Create HeadlessAuthManager instance for monitoring tests."""
        with patch("headless_auth.TokenManager") as mock_token_manager, patch(
            "headless_auth.NotificationSender"
        ) as mock_notification_sender:

            manager = headless_auth.HeadlessAuthManager(mock_config_file)
            manager.token_manager = mock_token_manager.return_value
            manager.notification_sender = mock_notification_sender.return_value
            return manager

    def test_monitor_loop_no_refresh_needed(self, auth_manager_with_monitoring):
        """Test monitoring loop when no refresh is needed."""
        auth_manager = auth_manager_with_monitoring
        auth_manager._monitoring = True

        # Mock token check to return no refresh needed
        auth_manager.token_manager.check_token_expiration.return_value = (False, None)

        # Mock time.sleep to avoid actual delays and stop after first iteration
        with patch("time.sleep") as mock_sleep, patch.object(
            auth_manager, "_perform_headless_auth"
        ) as mock_auth:

            # Set up sleep to stop monitoring after first check
            def stop_monitoring(*_):
                auth_manager._monitoring = False

            mock_sleep.side_effect = stop_monitoring

            auth_manager._monitor_loop()

            auth_manager.token_manager.check_token_expiration.assert_called_once()
            mock_auth.assert_not_called()

    def test_monitor_loop_refresh_needed_success(self, auth_manager_with_monitoring):
        """Test monitoring loop when refresh is needed and succeeds."""
        auth_manager = auth_manager_with_monitoring
        auth_manager._monitoring = True

        expiry = datetime.now() + timedelta(days=1)
        auth_manager.token_manager.check_token_expiration.return_value = (True, expiry)

        with patch("time.sleep") as mock_sleep, patch.object(
            auth_manager, "_perform_headless_auth", return_value=True
        ) as mock_auth, patch("headless_auth.logger") as mock_logger:

            # Stop monitoring after first check
            def stop_monitoring(*_):
                auth_manager._monitoring = False

            mock_sleep.side_effect = stop_monitoring

            auth_manager._monitor_loop()

            expected_expiry_info = (
                f"Current token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            mock_auth.assert_called_once_with(expected_expiry_info)
            mock_logger.info.assert_any_call("Background monitor detected token needs refresh")
            mock_logger.info.assert_any_call("Background token refresh completed successfully")

    def test_monitor_loop_refresh_needed_failure(self, auth_manager_with_monitoring):
        """Test monitoring loop when refresh is needed but fails."""
        auth_manager = auth_manager_with_monitoring
        auth_manager._monitoring = True

        expiry = datetime.now() + timedelta(days=1)
        auth_manager.token_manager.check_token_expiration.return_value = (True, expiry)

        with patch("time.sleep") as mock_sleep, patch.object(
            auth_manager, "_perform_headless_auth", return_value=False
        ) as mock_auth, patch("headless_auth.logger") as mock_logger:

            # Stop monitoring after first check
            def stop_monitoring(*_):
                auth_manager._monitoring = False

            mock_sleep.side_effect = stop_monitoring

            auth_manager._monitor_loop()

            mock_auth.assert_called_once()
            mock_logger.error.assert_called_with("Background token refresh failed")

    def test_monitor_loop_exception_handling(self, auth_manager_with_monitoring):
        """Test monitoring loop exception handling."""
        auth_manager = auth_manager_with_monitoring
        auth_manager._monitoring = True

        # Mock token check to raise exception
        auth_manager.token_manager.check_token_expiration.side_effect = Exception("Test error")

        with patch("time.sleep") as mock_sleep, patch("headless_auth.logger") as mock_logger:

            # Stop monitoring after exception handling
            call_count = 0

            def stop_after_retry(*_):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:  # Stop after retry sleep
                    auth_manager._monitoring = False

            mock_sleep.side_effect = stop_after_retry

            auth_manager._monitor_loop()

            mock_logger.exception.assert_called_with("Error in monitoring loop: Test error")
            # Should sleep 60 seconds on exception, then check again
            assert mock_sleep.call_count >= 1

    def test_monitor_loop_stops_when_monitoring_false(self, auth_manager_with_monitoring):
        """Test that monitoring loop stops when _monitoring is set to False."""
        auth_manager = auth_manager_with_monitoring
        auth_manager._monitoring = False  # Start with monitoring disabled

        with patch.object(auth_manager.token_manager, "check_token_expiration") as mock_check:
            auth_manager._monitor_loop()

            # Should not check token if monitoring is disabled
            mock_check.assert_not_called()
