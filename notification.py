"""Notification Module.

This module handles sending notifications via email, Discord, or Slack
when authentication is needed.
"""

import json
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional, Union

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Union[str, int]]:
    """Load configuration from config.json.

    Returns:
        Dict[str, Union[str, int]]: Configuration dictionary
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Error loading config: %s", e)
        return {}


def send_email_notification(auth_url: str, config: Optional[Dict] = None) -> bool:
    """Send an email notification with the authentication URL.

    Args:
        auth_url (str): The authentication URL to include in the email
        config (Optional[Dict]): Configuration dictionary, or None to load from file

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    if config is None:
        config = load_config()

    sender = config.get("NOTIFICATION_EMAIL_SENDER")
    receiver = config.get("NOTIFICATION_EMAIL_RECEIVER")
    smtp_server = config.get("SMTP_SERVER")
    smtp_port = config.get("SMTP_PORT", 587)
    smtp_username = config.get("SMTP_USERNAME")
    smtp_password = config.get("SMTP_PASSWORD")

    if not all([sender, receiver, smtp_server, smtp_username, smtp_password]):
        logger.error("Missing email configuration parameters")
        return False

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "FOGIS Calendar Sync - Authentication Required"
        message["From"] = sender
        message["To"] = receiver

        # Create plain text and HTML versions of the message
        text = f"""
        FOGIS Calendar Sync requires authentication.

        Please click the following link to authenticate:
        {auth_url}

        This link will be valid for 10 minutes.

        If you did not request this authentication, please ignore this email.
        """

        html = f"""
        <html>
        <body>
            <h2>FOGIS Calendar Sync - Authentication Required</h2>
            <p>Your FOGIS Calendar Sync application requires authentication.</p>
            <p><a href="{auth_url}">Click here to authenticate</a></p>
            <p>Or copy and paste this URL into your browser:</p>
            <p><code>{auth_url}</code></p>
            <p>This link will be valid for 10 minutes.</p>
            <p><em>If you did not request this authentication, please ignore this email.</em></p>
        </body>
        </html>
        """

        # Attach parts to the message
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))

        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try to log in to server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(smtp_username, smtp_password)
            server.sendmail(sender, receiver, message.as_string())

        logger.info("Email notification sent successfully to %s", receiver)
        return True
    except Exception as e:
        logger.error("Error sending email notification: %s", e)
        return False


def send_discord_notification(auth_url: str, config: Optional[Dict] = None) -> bool:
    """Send a Discord notification with the authentication URL.

    Args:
        auth_url (str): The authentication URL to include in the notification
        config (Optional[Dict]): Configuration dictionary, or None to load from file

    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if config is None:
        config = load_config()

    webhook_url = config.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.error("Missing Discord webhook URL")
        return False

    try:
        data = {
            "content": "FOGIS Calendar Sync requires authentication. Please click the link below to authenticate:",
            "embeds": [
                {
                    "title": "Authentication Link",
                    "description": auth_url,
                    "color": 5814783,  # Blue color
                    "footer": {"text": "This link will be valid for 10 minutes."},
                }
            ],
        }

        response = requests.post(webhook_url, json=data, timeout=30)
        response.raise_for_status()

        logger.info("Discord notification sent successfully")
        return True
    except Exception as e:
        logger.error("Error sending Discord notification: %s", e)
        return False


def send_slack_notification(auth_url: str, config: Optional[Dict] = None) -> bool:
    """Send a Slack notification with the authentication URL.

    Args:
        auth_url (str): The authentication URL to include in the notification
        config (Optional[Dict]): Configuration dictionary, or None to load from file

    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if config is None:
        config = load_config()

    webhook_url = config.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        logger.error("Missing Slack webhook URL")
        return False

    try:
        data = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*FOGIS Calendar Sync requires authentication*",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Please click this link to authenticate:\n<{auth_url}|Authenticate FOGIS Calendar Sync>",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "This link will be valid for 10 minutes."}
                    ],
                },
            ]
        }

        response = requests.post(webhook_url, json=data, timeout=30)
        response.raise_for_status()

        logger.info("Slack notification sent successfully")
        return True
    except Exception as e:
        logger.error("Error sending Slack notification: %s", e)
        return False


def send_notification(auth_url: str, config: Optional[Dict] = None) -> bool:
    """Send a notification using the configured method.

    Args:
        auth_url (str): The authentication URL to include in the notification
        config (Optional[Dict]): Configuration dictionary, or None to load from file

    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if config is None:
        config = load_config()

    # Always log the URL as a fallback
    logger.info("Authentication URL: %s", auth_url)

    notification_method = config.get("NOTIFICATION_METHOD", "email").lower()

    if notification_method == "email":
        return send_email_notification(auth_url, config)
    elif notification_method == "discord":
        return send_discord_notification(auth_url, config)
    elif notification_method == "slack":
        return send_slack_notification(auth_url, config)
    else:
        logger.warning("Unknown notification method: %s. Defaulting to email.", notification_method)
        return send_email_notification(auth_url, config)
