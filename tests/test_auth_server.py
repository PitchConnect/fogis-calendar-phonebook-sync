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
            "SMTP_PASSWORD": "test_password"
        }
        temp_file.write(json.dumps(config_data).encode())
        temp_file_name = temp_file.name
    
    # Mock the config.json file
    with mock.patch.object(auth_server, "load_config", return_value=config_data):
        yield config_data
    
    # Cleanup
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.mark.fast
def test_create_auth_server():
    """Test creating the authentication server."""
    app = auth_server.create_auth_server()
    
    assert isinstance(app, Flask)
    assert app.url_map.bind("localhost").match("/") is not None
    assert app.url_map.bind("localhost").match("/auth") is not None
    assert app.url_map.bind("localhost").match("/oauth2callback") is not None
    assert app.url_map.bind("localhost").match("/health") is not None


@pytest.mark.fast
def test_get_auth_url(mock_config_file):
    """Test getting the authentication URL."""
    auth_url = auth_server.get_auth_url()
    
    assert auth_url == f"http://{mock_config_file['AUTH_SERVER_HOST']}:{mock_config_file['AUTH_SERVER_PORT']}/auth"


@pytest.mark.fast
def test_initialize_oauth_flow(mock_config_file):
    """Test initializing the OAuth flow."""
    # Mock the Flow.from_client_secrets_file method
    with mock.patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file") as mock_flow:
        # Mock os.path.exists to return True for credentials.json
        with mock.patch("os.path.exists", return_value=True):
            result = auth_server.initialize_oauth_flow()
    
    assert result is True
    mock_flow.assert_called_once_with(
        mock_config_file["CREDENTIALS_FILE"],
        scopes=mock_config_file["SCOPES"],
        redirect_uri=f"http://{mock_config_file['AUTH_SERVER_HOST']}:{mock_config_file['AUTH_SERVER_PORT']}/oauth2callback"
    )


@pytest.mark.fast
def test_wait_for_auth():
    """Test waiting for authentication."""
    # Test timeout case
    auth_server.auth_success = False
    result = auth_server.wait_for_auth(timeout_seconds=0.1)
    assert result is False
    
    # Test success case
    auth_server.auth_success = True
    result = auth_server.wait_for_auth(timeout_seconds=0.1)
    assert result is True
    
    # Reset global variable
    auth_server.auth_success = False


@pytest.mark.integration
def test_start_headless_auth():
    """Test starting headless authentication."""
    # This is an integration test that would start the server
    # We'll mock most of the functionality to avoid actual server startup
    
    with mock.patch.object(auth_server, "start_auth_server", return_value=("localhost", 8080)):
        with mock.patch.object(auth_server, "initialize_oauth_flow", return_value=True):
            with mock.patch.object(auth_server, "get_auth_url", return_value="http://localhost:8080/auth"):
                with mock.patch("notification.send_notification", return_value=True):
                    with mock.patch.object(auth_server, "wait_for_auth", return_value=True):
                        with mock.patch.object(auth_server, "stop_auth_server"):
                            result = auth_server.start_headless_auth()
    
    assert result is True
