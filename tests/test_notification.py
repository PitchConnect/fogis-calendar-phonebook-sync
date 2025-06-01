"""Tests for the notification module."""

from unittest import mock

import pytest

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
def test_notification_sender_init(mock_config):
    """Test creating a NotificationSender instance."""
    sender = notification.NotificationSender(mock_config)

    assert sender.config == mock_config
    assert sender.method == "email"  # Default from mock_config


@pytest.mark.fast
def test_send_email_notification(mock_config):
    """Test sending an email notification."""
    auth_url = "https://example.com/auth"
    sender = notification.NotificationSender(mock_config)

    # Mock the SMTP server
    with mock.patch("smtplib.SMTP") as mock_smtp:
        # Configure the mock
        mock_server = mock_smtp.return_value.__enter__.return_value

        # Call the function using class-based API
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_server.login.assert_called_once_with(
        mock_config["SMTP_USERNAME"], mock_config["SMTP_PASSWORD"]
    )
    mock_server.send_message.assert_called_once()  # Updated method name


@pytest.mark.fast
def test_send_discord_notification(mock_config):
    """Test sending a Discord notification."""
    auth_url = "https://example.com/auth"
    mock_config["NOTIFICATION_METHOD"] = "discord"
    sender = notification.NotificationSender(mock_config)

    # Mock the urlopen method in the notification module
    with mock.patch("notification.urlopen") as mock_urlopen:
        # Configure the mock
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 204  # Discord webhook success status

        # Call the function using class-based API
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_urlopen.assert_called_once()
    # Verify the request was made
    assert mock_urlopen.call_args is not None


@pytest.mark.fast
def test_send_slack_notification(mock_config):
    """Test sending a Slack notification."""
    auth_url = "https://example.com/auth"
    mock_config["NOTIFICATION_METHOD"] = "slack"
    sender = notification.NotificationSender(mock_config)

    # Mock the urlopen method in the notification module
    with mock.patch("notification.urlopen") as mock_urlopen:
        # Configure the mock
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 200  # Slack webhook success status

        # Call the function using class-based API
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_urlopen.assert_called_once()
    # Verify the request was made
    assert mock_urlopen.call_args is not None


@pytest.mark.fast
def test_send_notification(mock_config):
    """Test sending a notification using the configured method."""
    auth_url = "https://example.com/auth"

    # Test email notification (default method)
    sender = notification.NotificationSender(mock_config)
    with mock.patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_email.assert_called_once()

    # Test Discord notification
    mock_config["NOTIFICATION_METHOD"] = "discord"
    sender = notification.NotificationSender(mock_config)
    with mock.patch.object(sender, "_send_discord", return_value=True) as mock_discord:
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_discord.assert_called_once()

    # Test Slack notification
    mock_config["NOTIFICATION_METHOD"] = "slack"
    sender = notification.NotificationSender(mock_config)
    with mock.patch.object(sender, "_send_slack", return_value=True) as mock_slack:
        result = sender.send_auth_notification(auth_url)

    assert result is True
    mock_slack.assert_called_once()
