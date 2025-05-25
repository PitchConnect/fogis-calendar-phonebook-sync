"""
Notification System for Headless Authentication

This module sends authentication notifications via email, Discord, or Slack
when re-authentication is needed in headless server environments.
"""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class NotificationSender:
    """Handles sending notifications via various methods."""
    
    def __init__(self, config: Dict):
        """
        Initialize the notification sender.
        
        Args:
            config: Configuration dictionary with notification settings
        """
        self.config = config
        self.method = config.get("NOTIFICATION_METHOD", "email").lower()
    
    def send_auth_notification(self, auth_url: str, expiry_info: str = "") -> bool:
        """
        Send authentication notification.
        
        Args:
            auth_url: Authorization URL for user to visit
            expiry_info: Information about token expiry
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        subject = "🔐 Google Authentication Required - FOGIS Calendar Sync"
        
        message = f"""
Google Authentication Required for FOGIS Calendar Sync

Your Google authentication token needs to be refreshed to continue syncing your FOGIS calendar and contacts.

{expiry_info}

To re-authenticate, please click the link below:

{auth_url}

SECURITY NOTICE:
- This link is valid for 10 minutes only
- Only click this link if you are expecting this authentication request
- The link will redirect you to Google's official authentication page

After authentication, your FOGIS sync service will continue running automatically.

---
FOGIS Calendar Sync Service
Automated notification system
        """.strip()
        
        # Log the notification regardless of method
        logger.info(f"Authentication required. URL: {auth_url}")
        
        success = False
        
        if self.method == "email":
            success = self._send_email(subject, message)
        elif self.method == "discord":
            success = self._send_discord(subject, message, auth_url)
        elif self.method == "slack":
            success = self._send_slack(subject, message, auth_url)
        else:
            logger.warning(f"Unknown notification method: {self.method}")
            success = False
        
        # Always log as fallback
        if not success:
            logger.warning("Failed to send notification via configured method")
            logger.info(f"AUTHENTICATION REQUIRED: Please visit {auth_url}")
        
        return success
    
    def _send_email(self, subject: str, message: str) -> bool:
        """Send email notification."""
        try:
            sender_email = self.config.get("NOTIFICATION_EMAIL_SENDER")
            receiver_email = self.config.get("NOTIFICATION_EMAIL_RECEIVER")
            smtp_server = self.config.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self.config.get("SMTP_PORT", 587)
            smtp_username = self.config.get("SMTP_USERNAME")
            smtp_password = self.config.get("SMTP_PASSWORD")
            
            if not all([sender_email, receiver_email, smtp_username, smtp_password]):
                logger.error("Missing email configuration parameters")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {receiver_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_discord(self, subject: str, message: str, auth_url: str) -> bool:
        """Send Discord webhook notification."""
        try:
            webhook_url = self.config.get("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                logger.error("Discord webhook URL not configured")
                return False
            
            # Create Discord embed
            embed = {
                "title": "🔐 Google Authentication Required",
                "description": "Your FOGIS Calendar Sync needs re-authentication",
                "color": 0xFF6B35,  # Orange color
                "fields": [
                    {
                        "name": "Action Required",
                        "value": f"[Click here to authenticate]({auth_url})",
                        "inline": False
                    },
                    {
                        "name": "Security Notice",
                        "value": "Only click if you are expecting this request. Link expires in 10 minutes.",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "FOGIS Calendar Sync Service"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            # Send webhook
            req = Request(webhook_url)
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(payload).encode('utf-8')
            
            with urlopen(req) as response:
                if response.status == 204:
                    logger.info("Discord notification sent successfully")
                    return True
                else:
                    logger.error(f"Discord webhook returned status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def _send_slack(self, subject: str, message: str, auth_url: str) -> bool:
        """Send Slack webhook notification."""
        try:
            webhook_url = self.config.get("SLACK_WEBHOOK_URL")
            if not webhook_url:
                logger.error("Slack webhook URL not configured")
                return False
            
            # Create Slack message
            payload = {
                "text": "🔐 Google Authentication Required",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔐 Google Authentication Required"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Your FOGIS Calendar Sync needs re-authentication to continue syncing."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"<{auth_url}|Click here to authenticate>"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "⚠️ Security Notice: Only click if you are expecting this request. Link expires in 10 minutes."
                            }
                        ]
                    }
                ]
            }
            
            # Send webhook
            req = Request(webhook_url)
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(payload).encode('utf-8')
            
            with urlopen(req) as response:
                if response.status == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.error(f"Slack webhook returned status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def send_success_notification(self) -> bool:
        """Send notification that authentication was successful."""
        subject = "✅ Google Authentication Successful - FOGIS Calendar Sync"
        message = """
Google Authentication Successful

Your FOGIS Calendar Sync has been successfully re-authenticated with Google.

The service will now continue syncing your calendar and contacts automatically.

No further action is required.

---
FOGIS Calendar Sync Service
Automated notification system
        """.strip()
        
        if self.method == "email":
            return self._send_email(subject, message)
        elif self.method == "discord":
            return self._send_discord_simple("✅ Authentication Successful", 
                                            "FOGIS Calendar Sync re-authentication completed successfully.")
        elif self.method == "slack":
            return self._send_slack_simple("✅ Authentication Successful", 
                                          "FOGIS Calendar Sync re-authentication completed successfully.")
        
        return False
    
    def _send_discord_simple(self, title: str, description: str) -> bool:
        """Send simple Discord message."""
        try:
            webhook_url = self.config.get("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                return False
            
            payload = {
                "embeds": [{
                    "title": title,
                    "description": description,
                    "color": 0x00FF00  # Green color
                }]
            }
            
            req = Request(webhook_url)
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(payload).encode('utf-8')
            
            with urlopen(req):
                return True
                
        except Exception:
            return False
    
    def _send_slack_simple(self, title: str, description: str) -> bool:
        """Send simple Slack message."""
        try:
            webhook_url = self.config.get("SLACK_WEBHOOK_URL")
            if not webhook_url:
                return False
            
            payload = {
                "text": f"{title}\n{description}"
            }
            
            req = Request(webhook_url)
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(payload).encode('utf-8')
            
            with urlopen(req):
                return True
                
        except Exception:
            return False
