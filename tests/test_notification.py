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


@pytest.mark.fast
def test_unknown_notification_method(mock_config):
    """Test handling of unknown notification method."""
    mock_config["NOTIFICATION_METHOD"] = "unknown_method"
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender.send_auth_notification("https://example.com/auth")

    assert result is False
    mock_logger.warning.assert_any_call("Unknown notification method: unknown_method")
    mock_logger.warning.assert_any_call(
        "Failed to send notification via configured method"
    )


@pytest.mark.fast
def test_notification_fallback_logging(mock_config):
    """Test that failed notifications fall back to logging."""
    sender = notification.NotificationSender(mock_config)
    auth_url = "https://example.com/auth"

    # Mock _send_email to return False (failure)
    with mock.patch.object(sender, "_send_email", return_value=False), mock.patch(
        "notification.logger"
    ) as mock_logger:
        result = sender.send_auth_notification(auth_url)

    assert result is False
    mock_logger.warning.assert_any_call(
        "Failed to send notification via configured method"
    )
    mock_logger.info.assert_any_call(
        f"AUTHENTICATION REQUIRED: Please visit {auth_url}"
    )


@pytest.mark.fast
def test_email_missing_configuration(mock_config):
    """Test email notification with missing configuration."""
    # Test missing sender email
    incomplete_config = mock_config.copy()
    del incomplete_config["NOTIFICATION_EMAIL_SENDER"]
    sender = notification.NotificationSender(incomplete_config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender._send_email("Test Subject", "Test Message")

    assert result is False
    mock_logger.error.assert_called_with("Missing email configuration parameters")


@pytest.mark.fast
def test_email_smtp_exception(mock_config):
    """Test email notification with SMTP exception."""
    sender = notification.NotificationSender(mock_config)

    # Mock SMTP to raise an exception
    with mock.patch("smtplib.SMTP") as mock_smtp, mock.patch(
        "notification.logger"
    ) as mock_logger:
        mock_smtp.side_effect = Exception("SMTP connection failed")

        result = sender._send_email("Test Subject", "Test Message")

    assert result is False
    mock_logger.error.assert_called_with(
        "Failed to send email notification: SMTP connection failed"
    )


@pytest.mark.fast
def test_discord_missing_webhook_url(mock_config):
    """Test Discord notification with missing webhook URL."""
    incomplete_config = mock_config.copy()
    del incomplete_config["DISCORD_WEBHOOK_URL"]
    sender = notification.NotificationSender(incomplete_config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender._send_discord(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with("Discord webhook URL not configured")


@pytest.mark.fast
def test_discord_webhook_error_status(mock_config):
    """Test Discord notification with error status from webhook."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen, mock.patch(
        "notification.logger"
    ) as mock_logger:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 400  # Error status

        result = sender._send_discord(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with("Discord webhook returned status 400")


@pytest.mark.fast
def test_discord_webhook_exception(mock_config):
    """Test Discord notification with webhook exception."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen, mock.patch(
        "notification.logger"
    ) as mock_logger:
        mock_urlopen.side_effect = Exception("Network error")

        result = sender._send_discord(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with(
        "Failed to send Discord notification: Network error"
    )


@pytest.mark.fast
def test_slack_missing_webhook_url(mock_config):
    """Test Slack notification with missing webhook URL."""
    incomplete_config = mock_config.copy()
    del incomplete_config["SLACK_WEBHOOK_URL"]
    sender = notification.NotificationSender(incomplete_config)

    with mock.patch("notification.logger") as mock_logger:
        result = sender._send_slack(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with("Slack webhook URL not configured")


@pytest.mark.fast
def test_slack_webhook_error_status(mock_config):
    """Test Slack notification with error status from webhook."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen, mock.patch(
        "notification.logger"
    ) as mock_logger:
        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.status = 500  # Error status

        result = sender._send_slack(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with("Slack webhook returned status 500")


@pytest.mark.fast
def test_slack_webhook_exception(mock_config):
    """Test Slack notification with webhook exception."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen, mock.patch(
        "notification.logger"
    ) as mock_logger:
        mock_urlopen.side_effect = Exception("Connection timeout")

        result = sender._send_slack(
            "Test Subject", "Test Message", "https://example.com/auth"
        )

    assert result is False
    mock_logger.error.assert_called_with(
        "Failed to send Slack notification: Connection timeout"
    )


@pytest.mark.fast
def test_send_success_notification_email(mock_config):
    """Test sending success notification via email."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_success_notification()

    assert result is True
    mock_email.assert_called_once()
    # Verify the subject and message contain success indicators
    call_args = mock_email.call_args[0]
    assert "✅" in call_args[0]  # Subject should contain success emoji
    assert "successful" in call_args[1].lower()  # Message should mention success


@pytest.mark.fast
def test_send_success_notification_discord(mock_config):
    """Test sending success notification via Discord."""
    mock_config["NOTIFICATION_METHOD"] = "discord"
    sender = notification.NotificationSender(mock_config)

    with mock.patch.object(
        sender, "_send_discord_simple", return_value=True
    ) as mock_discord:
        result = sender.send_success_notification()

    assert result is True
    mock_discord.assert_called_once_with(
        "✅ Authentication Successful",
        "FOGIS Calendar Sync re-authentication completed successfully.",
    )


@pytest.mark.fast
def test_send_success_notification_slack(mock_config):
    """Test sending success notification via Slack."""
    mock_config["NOTIFICATION_METHOD"] = "slack"
    sender = notification.NotificationSender(mock_config)

    with mock.patch.object(
        sender, "_send_slack_simple", return_value=True
    ) as mock_slack:
        result = sender.send_success_notification()

    assert result is True
    mock_slack.assert_called_once_with(
        "✅ Authentication Successful",
        "FOGIS Calendar Sync re-authentication completed successfully.",
    )


@pytest.mark.fast
def test_send_success_notification_unknown_method(mock_config):
    """Test sending success notification with unknown method."""
    mock_config["NOTIFICATION_METHOD"] = "unknown"
    sender = notification.NotificationSender(mock_config)

    result = sender.send_success_notification()

    assert result is False


@pytest.mark.fast
def test_discord_simple_success(mock_config):
    """Test _send_discord_simple method success."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is True
    mock_urlopen.assert_called_once()


@pytest.mark.fast
def test_discord_simple_missing_webhook(mock_config):
    """Test _send_discord_simple with missing webhook URL."""
    incomplete_config = mock_config.copy()
    del incomplete_config["DISCORD_WEBHOOK_URL"]
    sender = notification.NotificationSender(incomplete_config)

    result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_discord_simple_exception(mock_config):
    """Test _send_discord_simple with exception."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("Network error")

        result = sender._send_discord_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_slack_simple_success(mock_config):
    """Test _send_slack_simple method success."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is True
    mock_urlopen.assert_called_once()


@pytest.mark.fast
def test_slack_simple_missing_webhook(mock_config):
    """Test _send_slack_simple with missing webhook URL."""
    incomplete_config = mock_config.copy()
    del incomplete_config["SLACK_WEBHOOK_URL"]
    sender = notification.NotificationSender(incomplete_config)

    result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_slack_simple_exception(mock_config):
    """Test _send_slack_simple with exception."""
    sender = notification.NotificationSender(mock_config)

    with mock.patch("notification.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("Network error")

        result = sender._send_slack_simple("Test Title", "Test Description")

    assert result is False


@pytest.mark.fast
def test_notification_method_case_insensitive(mock_config):
    """Test that notification method is case insensitive."""
    # Test uppercase
    mock_config["NOTIFICATION_METHOD"] = "EMAIL"
    sender = notification.NotificationSender(mock_config)
    assert sender.method == "email"

    # Test mixed case
    mock_config["NOTIFICATION_METHOD"] = "DiScOrD"
    sender = notification.NotificationSender(mock_config)
    assert sender.method == "discord"


@pytest.mark.fast
def test_notification_with_expiry_info(mock_config):
    """Test notification with expiry information."""
    sender = notification.NotificationSender(mock_config)
    auth_url = "https://example.com/auth"
    expiry_info = "Token expires in 2 days"

    with mock.patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_auth_notification(auth_url, expiry_info)

    assert result is True
    mock_email.assert_called_once()
    # Verify expiry info is included in the message
    call_args = mock_email.call_args[0]
    assert expiry_info in call_args[1]  # Message should contain expiry info


@pytest.mark.fast
def test_notification_logging(mock_config):
    """Test that notifications are properly logged."""
    sender = notification.NotificationSender(mock_config)
    auth_url = "https://example.com/auth"

    with mock.patch.object(sender, "_send_email", return_value=True), mock.patch(
        "notification.logger"
    ) as mock_logger:
        sender.send_auth_notification(auth_url)

    # Verify the auth URL is logged
    mock_logger.info.assert_called_with(f"Authentication required. URL: {auth_url}")
