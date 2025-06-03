"""Tests for the notification module."""

import json
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


@pytest.mark.fast
def test_send_email_missing_config():
    """Test email sending with missing configuration."""
    config = {
        "NOTIFICATION_METHOD": "email",
        "NOTIFICATION_EMAIL_SENDER": "sender@example.com",
        # Missing receiver, username, password
    }
    sender = notification.NotificationSender(config)

    result = sender._send_email("Test Subject", "Test Message")

    assert result is False


@pytest.mark.fast
def test_send_email_smtp_error():
    """Test email sending with SMTP error."""
    config = {
        "NOTIFICATION_METHOD": "email",
        "NOTIFICATION_EMAIL_SENDER": "sender@example.com",
        "NOTIFICATION_EMAIL_RECEIVER": "receiver@example.com",
        "SMTP_SERVER": "smtp.example.com",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "username",
        "SMTP_PASSWORD": "password",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("smtplib.SMTP", side_effect=Exception("SMTP connection failed")):
        result = sender._send_email("Test Subject", "Test Message")

    assert result is False


@pytest.mark.fast
def test_send_discord_missing_webhook():
    """Test Discord sending without webhook URL."""
    config = {
        "NOTIFICATION_METHOD": "discord",
        # Missing DISCORD_WEBHOOK_URL
    }
    sender = notification.NotificationSender(config)

    result = sender._send_discord("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_discord_webhook_error():
    """Test Discord webhook with HTTP error."""
    config = {
        "NOTIFICATION_METHOD": "discord",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 400  # Bad request

        result = sender._send_discord("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_discord_exception():
    """Test Discord webhook with exception."""
    config = {
        "NOTIFICATION_METHOD": "discord",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen", side_effect=Exception("Network error")):
        result = sender._send_discord("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_slack_missing_webhook():
    """Test Slack sending without webhook URL."""
    config = {
        "NOTIFICATION_METHOD": "slack",
        # Missing SLACK_WEBHOOK_URL
    }
    sender = notification.NotificationSender(config)

    result = sender._send_slack("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_slack_webhook_error():
    """Test Slack webhook with HTTP error."""
    config = {
        "NOTIFICATION_METHOD": "slack",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 400  # Bad request

        result = sender._send_slack("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_slack_exception():
    """Test Slack webhook with exception."""
    config = {
        "NOTIFICATION_METHOD": "slack",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen", side_effect=Exception("Network error")):
        result = sender._send_slack("Test Subject", "Test Message", "https://example.com/auth")

    assert result is False


@pytest.mark.fast
def test_send_success_notification(mock_config):
    """Test sending success notification."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_success_notification()

    assert result is True
    mock_email.assert_called_once()
    # Verify the subject contains "Successful"
    call_args = mock_email.call_args[0]
    assert "Successful" in call_args[0]  # subject


@pytest.mark.fast
def test_send_success_notification_failure(mock_config):
    """Test sending success notification when email fails."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch.object(sender, "_send_email", return_value=False) as mock_email:
        result = sender.send_success_notification()

    assert result is False
    mock_email.assert_called_once()


@pytest.mark.fast
def test_unknown_notification_method():
    """Test handling unknown notification method."""
    config = {
        "NOTIFICATION_METHOD": "unknown_method",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender.send_auth_notification("https://example.com/auth")

    assert result is False
    mock_logger.warning.assert_called()


@pytest.mark.fast
def test_notification_fallback_logging():
    """Test that failed notifications still log the URL."""
    config = {
        "NOTIFICATION_METHOD": "email",
        # Missing required email config
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender.send_auth_notification("https://example.com/auth")

    assert result is False
    # Should log the auth URL as fallback
    mock_logger.info.assert_called()
    # Check that the URL was logged
    logged_calls = [
        call for call in mock_logger.info.call_args_list if "https://example.com/auth" in str(call)
    ]
    assert len(logged_calls) > 0


@pytest.mark.fast
def test_notification_method_case_insensitive():
    """Test that notification method is case insensitive."""
    config = {
        "NOTIFICATION_METHOD": "EMAIL",  # Uppercase
        "NOTIFICATION_EMAIL_SENDER": "sender@example.com",
        "NOTIFICATION_EMAIL_RECEIVER": "receiver@example.com",
        "SMTP_SERVER": "smtp.example.com",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "username",
        "SMTP_PASSWORD": "password",
    }
    sender = notification.NotificationSender(config)

    assert sender.method == "email"  # Should be lowercase

    with mock.patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_auth_notification("https://example.com/auth")

    assert result is True
    mock_email.assert_called_once()


@pytest.mark.fast
def test_send_success_notification_discord():
    """Test sending success notification via Discord."""
    config = {
        "NOTIFICATION_METHOD": "discord",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 204

        result = sender.send_success_notification()

    assert result is True
    mock_urlopen.assert_called_once()


@pytest.mark.fast
def test_send_success_notification_slack():
    """Test sending success notification via Slack."""
    config = {
        "NOTIFICATION_METHOD": "slack",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 200

        result = sender.send_success_notification()

    assert result is True
    mock_urlopen.assert_called_once()


@pytest.mark.fast
def test_send_discord_simple_success():
    """Test _send_discord_simple method."""
    config = {
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is True
    mock_urlopen.assert_called_once()

    # Verify the payload structure
    call_args = mock_urlopen.call_args[0][0]  # Get the Request object
    payload_data = call_args.data.decode("utf-8")
    payload = json.loads(payload_data)

    assert "embeds" in payload
    assert payload["embeds"][0]["title"] == "Test Title"
    assert payload["embeds"][0]["description"] == "Test Description"
    assert payload["embeds"][0]["color"] == 0x00FF00


@pytest.mark.fast
def test_send_discord_simple_missing_webhook():
    """Test _send_discord_simple with missing webhook URL."""
    config = {}  # No webhook URL
    sender = notification.NotificationSender(config)

    result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_send_discord_simple_exception():
    """Test _send_discord_simple with exception."""
    config = {
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen", side_effect=Exception("Network error")):
        result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_send_slack_simple_success():
    """Test _send_slack_simple method."""
    config = {
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is True
    mock_urlopen.assert_called_once()

    # Verify the payload structure
    call_args = mock_urlopen.call_args[0][0]  # Get the Request object
    payload_data = call_args.data.decode("utf-8")
    payload = json.loads(payload_data)

    assert payload["text"] == "Test Title\nTest Description"


@pytest.mark.fast
def test_send_slack_simple_missing_webhook():
    """Test _send_slack_simple with missing webhook URL."""
    config = {}  # No webhook URL
    sender = notification.NotificationSender(config)

    result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_send_slack_simple_exception():
    """Test _send_slack_simple with exception."""
    config = {
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }
    sender = notification.NotificationSender(config)

    with mock.patch("notification.urlopen", side_effect=Exception("Network error")):
        result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_send_success_notification_unknown_method():
    """Test success notification with unknown method."""
    config = {
        "NOTIFICATION_METHOD": "unknown_method",
    }
    sender = notification.NotificationSender(config)

    result = sender.send_success_notification()

    assert result is False
