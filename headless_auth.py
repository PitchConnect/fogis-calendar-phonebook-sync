"""
Headless Authentication Integration

This module integrates the headless authentication system with the main
FOGIS Calendar Sync application.
"""

import atexit
import json
import logging
import os
import sys
import threading
import time
from typing import Dict, Optional

from auth_server import AuthServer
from notification import NotificationSender
from token_manager import TokenManager

logger = logging.getLogger(__name__)


class HeadlessAuthManager:
    """Manages headless authentication for the FOGIS Calendar Sync application."""

    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the headless authentication manager.

        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.token_manager = TokenManager(
            self.config,
            credentials_file=self.config.get("CREDENTIALS_FILE", "credentials.json"),
            token_file="token.json",
        )
        self.notification_sender = NotificationSender(self.config)
        self.auth_server = None
        self._monitoring = False
        self._monitor_thread = None

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_file}: {e}")
            return {}

    def get_valid_credentials(self):
        """
        Get valid Google credentials, handling headless re-authentication if needed.

        Returns:
            Valid Google OAuth credentials or None if authentication failed
        """
        # Check if we need proactive refresh
        needs_refresh, expiry = self.token_manager.check_token_expiration()

        if needs_refresh:
            logger.info("Token needs refresh - initiating headless authentication")

            expiry_info = ""
            if expiry:
                expiry_info = f"Current token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}"

            success = self._perform_headless_auth(expiry_info)
            if not success:
                logger.error("Headless authentication failed")
                return None

        # Get credentials
        credentials = self.token_manager.get_credentials()
        if not credentials:
            logger.error("No valid credentials available")
            return None

        logger.info("Valid credentials obtained")
        return credentials

    def _perform_headless_auth(self, expiry_info: str = "") -> bool:
        """
        Perform headless authentication flow.

        Args:
            expiry_info: Information about token expiry

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Create and start auth server
            self.auth_server = AuthServer(self.config, self.token_manager)
            auth_url = self.auth_server.start()

            logger.info(f"Authentication server started, auth URL: {auth_url}")

            # Send notification
            notification_sent = self.notification_sender.send_auth_notification(
                auth_url, expiry_info
            )

            if not notification_sent:
                logger.warning("Failed to send notification, but continuing with auth flow")

            # Wait for authentication
            logger.info("Waiting for user authentication...")
            success = self.auth_server.wait_for_auth(timeout=600)  # 10 minutes

            if success:
                logger.info("Headless authentication completed successfully")
                # Send success notification
                self.notification_sender.send_success_notification()
                return True
            else:
                logger.error("Headless authentication failed or timed out")
                return False

        except Exception as e:
            logger.exception(f"Error during headless authentication: {e}")
            return False
        finally:
            # Clean up auth server
            if self.auth_server:
                self.auth_server.stop()
                self.auth_server = None

    def start_monitoring(self):
        """Start background monitoring for token expiration."""
        if self._monitoring:
            logger.warning("Token monitoring already running")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

        logger.info("Started background token monitoring")

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Stopped background token monitoring")

    def _monitor_loop(self):
        """Background monitoring loop."""
        check_interval = 3600  # Check every hour

        while self._monitoring:
            try:
                needs_refresh, expiry = self.token_manager.check_token_expiration()

                if needs_refresh:
                    logger.info("Background monitor detected token needs refresh")

                    expiry_info = ""
                    if expiry:
                        expiry_info = (
                            f"Current token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        )

                    success = self._perform_headless_auth(expiry_info)
                    if success:
                        logger.info("Background token refresh completed successfully")
                    else:
                        logger.error("Background token refresh failed")
                        # Continue monitoring - maybe next time will work

                # Sleep for check interval
                for _ in range(check_interval):
                    if not self._monitoring:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")
                # Sleep a bit before retrying
                time.sleep(60)

    def get_token_status(self) -> Dict:
        """Get current token status information."""
        return self.token_manager.get_token_info()

    def force_refresh(self) -> bool:
        """Force a token refresh."""
        logger.info("Forcing token refresh")
        return self._perform_headless_auth("Manual refresh requested")


def integrate_with_existing_auth(config_dict: Dict, headless_mode: bool = False):
    """
    Integration function to replace existing authorization logic.

    Args:
        config_dict: Configuration dictionary
        headless_mode: Whether to use headless mode

    Returns:
        Valid Google credentials or None
    """
    if not headless_mode:
        # Fall back to original authorization method
        logger.info("Using standard (non-headless) authentication")
        return None  # Let the original method handle it

    logger.info("Using headless authentication mode")

    # Create headless auth manager
    auth_manager = HeadlessAuthManager()

    # Get valid credentials
    credentials = auth_manager.get_valid_credentials()

    if credentials:
        # Start background monitoring
        auth_manager.start_monitoring()

        # Store reference for cleanup (you might want to handle this differently)
        if not hasattr(integrate_with_existing_auth, "_auth_managers"):
            integrate_with_existing_auth._auth_managers = []
        integrate_with_existing_auth._auth_managers.append(auth_manager)

    return credentials


def cleanup_auth_managers():
    """Clean up any running auth managers."""
    if hasattr(integrate_with_existing_auth, "_auth_managers"):
        for manager in integrate_with_existing_auth._auth_managers:
            manager.stop_monitoring()
        integrate_with_existing_auth._auth_managers.clear()


# Register cleanup function to run on exit
atexit.register(cleanup_auth_managers)
