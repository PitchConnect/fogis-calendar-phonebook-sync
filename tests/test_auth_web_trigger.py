"""Tests for auth_web_trigger module."""

import json
import threading
from unittest.mock import MagicMock, patch

import pytest

import auth_web_trigger


@pytest.fixture
def mock_auth_manager():
    """Return a mock HeadlessAuthManager for testing."""
    mock_manager = MagicMock()
    mock_manager.get_token_status.return_value = {
        "valid": True,
        "expired": False,
        "needs_refresh": False,
        "expiry": "2024-12-31T23:59:59",
        "has_refresh_token": True,
    }
    mock_manager.force_refresh.return_value = True
    return mock_manager


@pytest.fixture
def client():
    """Return a test client for the Flask app."""
    auth_web_trigger.app.config["TESTING"] = True
    with auth_web_trigger.app.test_client() as client:
        yield client


class TestIndexRoute:
    """Test cases for the index route."""

    def test_index_route_success(self, client, mock_auth_manager):
        """Test successful index route rendering."""
        # Reset global auth_manager to ensure clean test
        auth_web_trigger.auth_manager = None

        with patch(
            "auth_web_trigger.HeadlessAuthManager", return_value=mock_auth_manager
        ):
            response = client.get("/")

            assert response.status_code == 200
            assert b"FOGIS Authentication Manager" in response.data
            assert b"Current Token Status" in response.data
            assert b"Valid:</strong> True" in response.data

    def test_index_route_creates_auth_manager(self, client):
        """Test that index route creates auth manager when none exists."""
        # Reset global auth_manager
        auth_web_trigger.auth_manager = None

        with patch("auth_web_trigger.HeadlessAuthManager") as mock_class:
            mock_instance = MagicMock()
            mock_instance.get_token_status.return_value = {
                "valid": False,
                "expired": True,
                "needs_refresh": True,
                "expiry": None,
                "has_refresh_token": False,
            }
            mock_class.return_value = mock_instance

            response = client.get("/")

            assert response.status_code == 200
            mock_class.assert_called_once()
            assert auth_web_trigger.auth_manager == mock_instance

    def test_index_route_uses_existing_auth_manager(self, client, mock_auth_manager):
        """Test that index route uses existing auth manager."""
        auth_web_trigger.auth_manager = mock_auth_manager

        with patch("auth_web_trigger.HeadlessAuthManager") as mock_class:
            response = client.get("/")

            assert response.status_code == 200
            mock_class.assert_not_called()
            mock_auth_manager.get_token_status.assert_called_once()

    def test_index_route_token_expired(self, client):
        """Test index route with expired token."""
        # Reset global auth_manager to ensure clean test
        auth_web_trigger.auth_manager = None

        mock_manager = MagicMock()
        mock_manager.get_token_status.return_value = {
            "valid": False,
            "expired": True,
            "needs_refresh": False,  # Changed to False to trigger error message
            "expiry": None,
            "has_refresh_token": False,
        }

        with patch("auth_web_trigger.HeadlessAuthManager", return_value=mock_manager):
            response = client.get("/")

            assert response.status_code == 200
            assert b"No valid token found" in response.data
            assert b"Authentication required" in response.data

    def test_index_route_token_needs_refresh(self, client):
        """Test index route with token that needs refresh."""
        # Reset global auth_manager to ensure clean test
        auth_web_trigger.auth_manager = None

        mock_manager = MagicMock()
        mock_manager.get_token_status.return_value = {
            "valid": True,
            "expired": False,
            "needs_refresh": True,
            "expiry": "2024-01-01T12:00:00",
            "has_refresh_token": True,
        }

        with patch("auth_web_trigger.HeadlessAuthManager", return_value=mock_manager):
            response = client.get("/")

            assert response.status_code == 200
            assert b"Token needs refresh" in response.data
            assert b"You should re-authenticate soon" in response.data


class TestRestartAuthRoute:
    """Test cases for the restart auth route."""

    def test_restart_auth_success(self, client, mock_auth_manager):
        """Test successful authentication restart."""
        auth_web_trigger.auth_manager = mock_auth_manager

        with patch("auth_web_trigger.logger") as mock_logger, patch(
            "threading.Thread"
        ) as mock_thread:

            response = client.post("/restart-auth")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "Authentication process started" in data["message"]

            mock_logger.info.assert_called_with(
                "Web interface triggered authentication restart"
            )
            mock_thread.assert_called_once()

    def test_restart_auth_creates_auth_manager(self, client):
        """Test restart auth creates auth manager when none exists."""
        auth_web_trigger.auth_manager = None

        with patch("auth_web_trigger.HeadlessAuthManager") as mock_class, patch(
            "threading.Thread"
        ) as mock_thread:

            mock_instance = MagicMock()
            mock_instance.force_refresh.return_value = True
            mock_class.return_value = mock_instance

            response = client.post("/restart-auth")

            assert response.status_code == 200
            mock_class.assert_called_once()
            mock_thread.assert_called_once()

    def test_restart_auth_exception_handling(self, client):
        """Test restart auth exception handling."""
        auth_web_trigger.auth_manager = None

        with patch(
            "auth_web_trigger.HeadlessAuthManager",
            side_effect=Exception("Auth manager error"),
        ), patch("auth_web_trigger.logger") as mock_logger:

            response = client.post("/restart-auth")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Error: Auth manager error" in data["message"]

            mock_logger.exception.assert_called()

    def test_restart_auth_thread_execution(self, client, mock_auth_manager):
        """Test that the authentication thread executes properly."""
        auth_web_trigger.auth_manager = mock_auth_manager

        # Track thread execution
        thread_executed = threading.Event()

        def mock_thread_init(target=None, *args, **kwargs):
            # Execute the target function immediately for testing
            if target:
                target()
                thread_executed.set()
            return MagicMock()

        with patch("threading.Thread", side_effect=mock_thread_init), patch(
            "auth_web_trigger.logger"
        ) as mock_logger:

            response = client.post("/restart-auth")

            assert response.status_code == 200
            assert thread_executed.is_set()
            mock_auth_manager.force_refresh.assert_called_once()
            mock_logger.info.assert_any_call(
                "Web-triggered authentication completed successfully"
            )

    def test_restart_auth_thread_failure(self, client, mock_auth_manager):
        """Test authentication thread failure handling."""
        auth_web_trigger.auth_manager = mock_auth_manager
        mock_auth_manager.force_refresh.return_value = False

        # Track thread execution
        thread_executed = threading.Event()

        def mock_thread_init(target=None, *args, **kwargs):
            if target:
                target()
                thread_executed.set()
            return MagicMock()

        with patch("threading.Thread", side_effect=mock_thread_init), patch(
            "auth_web_trigger.logger"
        ) as mock_logger:

            response = client.post("/restart-auth")

            assert response.status_code == 200
            assert thread_executed.is_set()
            mock_logger.error.assert_any_call("Web-triggered authentication failed")

    def test_restart_auth_thread_exception(self, client, mock_auth_manager):
        """Test authentication thread exception handling."""
        auth_web_trigger.auth_manager = mock_auth_manager
        mock_auth_manager.force_refresh.side_effect = Exception("Force refresh error")

        # Track thread execution
        thread_executed = threading.Event()

        def mock_thread_init(target=None, *args, **kwargs):
            if target:
                target()
                thread_executed.set()
            return MagicMock()

        with patch("threading.Thread", side_effect=mock_thread_init), patch(
            "auth_web_trigger.logger"
        ) as mock_logger:

            response = client.post("/restart-auth")

            assert response.status_code == 200
            assert thread_executed.is_set()
            mock_logger.exception.assert_called()


class TestStatusRoute:
    """Test cases for the status API route."""

    def test_status_route_success(self, client, mock_auth_manager):
        """Test successful status route."""
        auth_web_trigger.auth_manager = mock_auth_manager

        response = client.get("/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["valid"] is True
        assert data["expired"] is False
        assert data["needs_refresh"] is False

    def test_status_route_creates_auth_manager(self, client):
        """Test status route creates auth manager when none exists."""
        auth_web_trigger.auth_manager = None

        with patch("auth_web_trigger.HeadlessAuthManager") as mock_class:
            mock_instance = MagicMock()
            mock_instance.get_token_status.return_value = {
                "valid": False,
                "expired": True,
                "needs_refresh": True,
                "expiry": None,
                "has_refresh_token": False,
            }
            mock_class.return_value = mock_instance

            response = client.get("/status")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["valid"] is False
            assert data["expired"] is True
            mock_class.assert_called_once()

    def test_status_route_uses_existing_auth_manager(self, client, mock_auth_manager):
        """Test status route uses existing auth manager."""
        auth_web_trigger.auth_manager = mock_auth_manager

        with patch("auth_web_trigger.HeadlessAuthManager") as mock_class:
            response = client.get("/status")

            assert response.status_code == 200
            mock_class.assert_not_called()
            mock_auth_manager.get_token_status.assert_called_once()


class TestMainFunction:
    """Test cases for the main function."""

    def test_main_function(self):
        """Test main function execution."""
        with patch("auth_web_trigger.app.run") as mock_run, patch(
            "builtins.print"
        ) as mock_print:

            auth_web_trigger.main()

            mock_run.assert_called_once_with(host="0.0.0.0", port=8090, debug=False)

            # Check that informational messages were printed
            print_calls = [args[0][0] for args in mock_print.call_args_list]
            assert any(
                "Starting FOGIS Authentication Web Manager" in msg
                for msg in print_calls
            )
            assert any("http://localhost:8090" in msg for msg in print_calls)
            assert any("Bookmark this URL" in msg for msg in print_calls)


class TestGlobalVariables:
    """Test cases for global variables and module setup."""

    def test_app_creation(self):
        """Test Flask app creation."""
        assert auth_web_trigger.app is not None
        assert auth_web_trigger.app.name == "auth_web_trigger"

    def test_initial_auth_manager_state(self):
        """Test initial auth manager state."""
        # Reset to initial state
        auth_web_trigger.auth_manager = None
        assert auth_web_trigger.auth_manager is None

    def test_html_template_exists(self):
        """Test HTML template is defined."""
        assert auth_web_trigger.HTML_TEMPLATE is not None
        assert "FOGIS Authentication Manager" in auth_web_trigger.HTML_TEMPLATE
        assert "Current Token Status" in auth_web_trigger.HTML_TEMPLATE
