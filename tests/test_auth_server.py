"""Tests for the auth_server module."""

import json
import os
import tempfile
from unittest import mock

import pytest
from flask import Flask

import auth_server


@pytest.fixture
def mock_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        config_data = {
            "AUTH_SERVER_HOST": "localhost",
            "AUTH_SERVER_PORT": 8080,
            "CREDENTIALS_FILE": "credentials.json",
            "SCOPES": ["https://www.googleapis.com/auth/calendar"],
            "NOTIFICATION_METHOD": "email",
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_PORT": 587,
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test_password",
        }
        temp_file.write(json.dumps(config_data).encode())
        temp_file_name = temp_file.name

    # Return config data directly (no need to mock load_config since develop doesn't use it)
    yield config_data

    # Cleanup
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.mark.fast
def test_create_auth_server():
    """Test creating the authentication server."""
    from token_manager import TokenManager

    # Create a mock token manager
    mock_token_manager = mock.Mock(spec=TokenManager)

    # Create auth server with develop's class-based API
    server = auth_server.AuthServer(
        {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}, mock_token_manager
    )

    assert hasattr(server, "app")
    assert isinstance(server.app, Flask)
    # Check that the callback route exists
    assert any(rule.rule == "/callback" for rule in server.app.url_map.iter_rules())
    assert any(rule.rule == "/health" for rule in server.app.url_map.iter_rules())


@pytest.mark.fast
def test_get_auth_url(mock_config_file):
    """Test getting the authentication URL."""
    from token_manager import TokenManager

    # Create a mock token manager
    mock_token_manager = mock.Mock(spec=TokenManager)

    # Create auth server with develop's class-based API
    server = auth_server.AuthServer(mock_config_file, mock_token_manager)

    # The get_auth_url method returns None if server not started
    auth_url = server.get_auth_url()
    assert auth_url is None  # Server not started yet


@pytest.mark.unit
def test_auth_server_initialization():
    """Test AuthServer initialization with various configurations."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    # Test with minimal config
    config = {}
    server = auth_server.AuthServer(config, mock_token_manager)
    assert server.host == "localhost"  # default
    assert server.port == 8080  # default
    assert server.timeout_seconds == 600
    assert server.auth_completed is False
    assert server.auth_success is False

    # Test with custom config
    config = {"AUTH_SERVER_HOST": "0.0.0.0", "AUTH_SERVER_PORT": 9090}
    server = auth_server.AuthServer(config, mock_token_manager)
    assert server.host == "0.0.0.0"
    assert server.port == 9090


@pytest.mark.unit
def test_auth_server_start_stop():
    """Test starting and stopping the auth server."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)
    mock_token_manager.initiate_auth_flow.return_value = "http://test.auth.url"

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)

    with mock.patch("auth_server.make_server") as mock_make_server, mock.patch(
        "threading.Thread"
    ) as mock_thread:

        mock_server_instance = mock.Mock()
        mock_make_server.return_value = mock_server_instance
        mock_thread_instance = mock.Mock()
        mock_thread.return_value = mock_thread_instance

        # Test start
        auth_url = server.start()

        assert auth_url is not None
        assert "http://test.auth.url" in auth_url
        assert "state=" in auth_url
        assert server.state is not None
        mock_make_server.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        # Test stop
        server.stop()
        mock_server_instance.shutdown.assert_called_once()
        mock_thread_instance.join.assert_called_once_with(timeout=5)


@pytest.mark.unit
def test_auth_server_callback_success():
    """Test successful OAuth callback handling."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)
    mock_token_manager.complete_auth_flow.return_value = True

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "test_state_123"

    with server.app.test_client() as client:
        response = client.get("/callback?code=test_auth_code&state=test_state_123")

        assert response.status_code == 200
        assert b"Authentication Successful" in response.data
        assert server.auth_completed is True
        assert server.auth_success is True
        mock_token_manager.complete_auth_flow.assert_called_once()


@pytest.mark.unit
def test_auth_server_callback_invalid_state():
    """Test OAuth callback with invalid state parameter."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "correct_state"

    with server.app.test_client() as client:
        response = client.get("/callback?code=test_auth_code&state=wrong_state")

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Invalid state parameter"
        assert data["success"] is False


@pytest.mark.unit
def test_auth_server_callback_oauth_error():
    """Test OAuth callback with error parameter."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "test_state"

    with server.app.test_client() as client:
        response = client.get("/callback?error=access_denied&state=test_state")

        assert response.status_code == 400
        data = response.get_json()
        assert "OAuth error: access_denied" in data["error"]
        assert data["success"] is False
        assert server.auth_completed is True
        assert server.auth_success is False


@pytest.mark.unit
def test_auth_server_callback_no_code():
    """Test OAuth callback without authorization code."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "test_state"

    with server.app.test_client() as client:
        response = client.get("/callback?state=test_state")

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "No authorization code received"
        assert data["success"] is False


@pytest.mark.unit
def test_auth_server_callback_auth_failure():
    """Test OAuth callback when auth flow completion fails."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)
    mock_token_manager.complete_auth_flow.return_value = False

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "test_state"

    with server.app.test_client() as client:
        response = client.get("/callback?code=test_auth_code&state=test_state")

        assert response.status_code == 500
        assert b"Authentication Failed" in response.data
        assert server.auth_completed is True
        assert server.auth_success is False


@pytest.mark.unit
def test_auth_server_callback_exception():
    """Test OAuth callback when an exception occurs."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)
    mock_token_manager.complete_auth_flow.side_effect = Exception("Test error")

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)
    server.state = "test_state"

    with server.app.test_client() as client:
        response = client.get("/callback?code=test_auth_code&state=test_state")

        assert response.status_code == 500
        data = response.get_json()
        assert "Internal error" in data["error"]
        assert data["success"] is False
        assert server.auth_completed is True
        assert server.auth_success is False


@pytest.mark.unit
def test_auth_server_health_endpoint():
    """Test health check endpoint."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)

    with server.app.test_client() as client:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "running"
        assert data["auth_completed"] is False
        assert data["auth_success"] is False


@pytest.mark.unit
def test_auth_server_wait_for_auth():
    """Test waiting for authentication completion."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)

    # Test successful auth
    server.auth_completed = True
    server.auth_success = True
    result = server.wait_for_auth(timeout=1)
    assert result is True

    # Test failed auth
    server.auth_success = False
    result = server.wait_for_auth(timeout=1)
    assert result is False

    # Test timeout
    server.auth_completed = False
    with mock.patch("time.sleep"):  # Speed up test
        result = server.wait_for_auth(timeout=0.1)
        assert result is False


@pytest.mark.unit
def test_auth_server_get_auth_url_with_server():
    """Test getting auth URL when server is running."""
    from token_manager import TokenManager

    mock_token_manager = mock.Mock(spec=TokenManager)

    config = {"AUTH_SERVER_HOST": "localhost", "AUTH_SERVER_PORT": 8080}
    server = auth_server.AuthServer(config, mock_token_manager)

    # Mock server and state
    server.server = mock.Mock()
    server.state = "test_state"

    auth_url = server.get_auth_url()
    assert auth_url is not None
    assert "localhost:8080/callback" in auth_url


# @pytest.mark.fast
# def test_initialize_oauth_flow(mock_config_file):
#     """Test initializing the OAuth flow."""
#     # This test needs to be updated for the class-based API
#     pass

# @pytest.mark.fast
# def test_wait_for_auth():
#     """Test waiting for authentication."""
#     # This test needs to be updated for the class-based API
#     pass

# @pytest.mark.integration
# def test_start_headless_auth():
#     """Test starting headless authentication."""
#     # This test needs to be updated for the class-based API
#     pass
