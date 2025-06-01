"""Tests for the notification module."""

import json
import tempfile
from unittest import mock

import pytest
import requests

import notification


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        "NOTIFICATION_METHOD": "email",
        "NOTIFICATION_EMAIL_SENDER": "sender@example.com",
        "NOTIFICATION_EMAIL_RECEIVER": "receiver@example.com",
        "SMTP_SERVER": "smtp.example.com",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "username",
        "SMTP_PASSWORD": "password",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }


@pytest.mark.fast
def test_load_config():
    """Test loading configuration from file."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        config_data = {
            "NOTIFICATION_METHOD": "email",
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
        }
        json.dump(config_data, temp_file)

    # Mock the open function to use our temporary file
    with mock.patch("builtins.open", mock.mock_open(read_data=json.dumps(config_data))):
        config = notification.load_config()

    assert config == config_data


@pytest.mark.fast
def test_send_email_notification(mock_config):
    """Test sending an email notification."""
    auth_url = "https://example.com/auth"

    # Mock the SMTP server
    with mock.patch("smtplib.SMTP") as mock_smtp:
        # Configure the mock
        mock_server = mock_smtp.return_value.__enter__.return_value

        # Call the function
        result = notification.send_email_notification(auth_url, mock_config)

    assert result is True
    mock_server.login.assert_called_once_with(
        mock_config["SMTP_USERNAME"], mock_config["SMTP_PASSWORD"]
    )
    mock_server.sendmail.assert_called_once()
    assert mock_server.sendmail.call_args[0][0] == mock_config["NOTIFICATION_EMAIL_SENDER"]
    assert mock_server.sendmail.call_args[0][1] == mock_config["NOTIFICATION_EMAIL_RECEIVER"]


@pytest.mark.fast
def test_send_discord_notification(mock_config):
    """Test sending a Discord notification."""
    auth_url = "https://example.com/auth"

    # Mock the requests.post method
    with mock.patch("requests.post") as mock_post:
        # Configure the mock
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None

        # Call the function
        result = notification.send_discord_notification(auth_url, mock_config)

    assert result is True
    mock_post.assert_called_once_with(mock_config["DISCORD_WEBHOOK_URL"], json=mock.ANY, timeout=30)
    # Verify the payload contains the auth_url
    assert auth_url in str(mock_post.call_args[1]["json"])


@pytest.mark.fast
def test_send_slack_notification(mock_config):
    """Test sending a Slack notification."""
    auth_url = "https://example.com/auth"

    # Mock the requests.post method
    with mock.patch("requests.post") as mock_post:
        # Configure the mock
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None

        # Call the function
        result = notification.send_slack_notification(auth_url, mock_config)

    assert result is True
    mock_post.assert_called_once_with(mock_config["SLACK_WEBHOOK_URL"], json=mock.ANY, timeout=30)
    # Verify the payload contains the auth_url
    assert auth_url in str(mock_post.call_args[1]["json"])


@pytest.mark.fast
def test_send_notification(mock_config):
    """Test sending a notification using the configured method."""
    auth_url = "https://example.com/auth"

    # Test email notification
    with mock.patch.object(
        notification, "send_email_notification", return_value=True
    ) as mock_email:
        result = notification.send_notification(auth_url, mock_config)

    assert result is True
    mock_email.assert_called_once_with(auth_url, mock_config)

    # Test Discord notification
    mock_config["NOTIFICATION_METHOD"] = "discord"
    with mock.patch.object(
        notification, "send_discord_notification", return_value=True
    ) as mock_discord:
        result = notification.send_notification(auth_url, mock_config)

    assert result is True
    mock_discord.assert_called_once_with(auth_url, mock_config)

    # Test Slack notification
    mock_config["NOTIFICATION_METHOD"] = "slack"
    with mock.patch.object(
        notification, "send_slack_notification", return_value=True
    ) as mock_slack:
        result = notification.send_notification(auth_url, mock_config)

    assert result is True
    mock_slack.assert_called_once_with(auth_url, mock_config)
