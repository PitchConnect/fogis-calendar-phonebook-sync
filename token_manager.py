"""
Token Manager for Headless Google Authentication

This module manages Google OAuth tokens, tracks expiration, and handles
proactive refresh for headless server environments.
"""

import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages Google OAuth tokens with proactive refresh capabilities."""

    def __init__(
        self,
        config: Dict,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
    ):
        """
        Initialize the token manager.

        Args:
            config: Configuration dictionary with SCOPES and other settings
            credentials_file: Path to Google OAuth credentials file
            token_file: Path to store/load tokens
        """
        self.config = config
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = config.get(
            "SCOPES",
            [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
            ],
        )
        self.refresh_buffer_days = config.get("TOKEN_REFRESH_BUFFER_DAYS", 6)
        self._credentials = None

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, refreshing if necessary.

        Returns:
            Valid Google OAuth credentials or None if authentication needed
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to load existing token
        if os.path.exists(self.token_file):
            try:
                self._credentials = Credentials.from_authorized_user_file(
                    self.token_file, self.scopes
                )
                logger.info("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
                self._credentials = None

        # Refresh if expired but refreshable
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                request = google.auth.transport.requests.Request()
                self._credentials.refresh(request)
                self._save_token()
                logger.info("Successfully refreshed expired token")
                return self._credentials
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                self._credentials = None

        # Return valid credentials or None
        if self._credentials and self._credentials.valid:
            return self._credentials

        return None

    def check_token_expiration(self) -> Tuple[bool, Optional[datetime]]:
        """
        Check if token needs proactive refresh.

        Returns:
            Tuple of (needs_refresh, expiry_datetime)
        """
        credentials = self.get_credentials()
        if not credentials:
            return True, None

        if not credentials.expiry:
            # No expiry info, assume it's good for now
            return False, None

        # Check if we're within the buffer period
        buffer_time = timedelta(days=self.refresh_buffer_days)
        needs_refresh = datetime.utcnow() + buffer_time >= credentials.expiry

        return needs_refresh, credentials.expiry

    def initiate_auth_flow(self) -> str:
        """
        Initiate OAuth flow and return authorization URL.

        Returns:
            Authorization URL for user to visit
        """
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

        # Configure redirect URI for headless mode
        redirect_uri = f"http://{self.config.get('AUTH_SERVER_HOST', 'localhost')}:{self.config.get('AUTH_SERVER_PORT', 8080)}/callback"
        flow = Flow.from_client_secrets_file(
            self.credentials_file, self.scopes, redirect_uri=redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",  # Force consent to get refresh token
        )

        # Store flow for later use
        self._flow = flow

        return auth_url

    def complete_auth_flow(self, authorization_response: str) -> bool:
        """
        Complete OAuth flow with authorization response.

        Args:
            authorization_response: Full callback URL with authorization code

        Returns:
            True if successful, False otherwise
        """
        try:
            if not hasattr(self, "_flow"):
                logger.error("No active auth flow found")
                return False

            self._flow.fetch_token(authorization_response=authorization_response)
            self._credentials = self._flow.credentials
            self._save_token()

            logger.info("Successfully completed authentication flow")
            return True

        except Exception as e:
            logger.error(f"Failed to complete auth flow: {e}")
            return False

    def _save_token(self):
        """Save credentials to token file."""
        try:
            with open(self.token_file, "w") as token_file:
                token_file.write(self._credentials.to_json())
            logger.info(f"Token saved to {self.token_file}")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def get_token_info(self) -> Dict:
        """
        Get information about current token status.

        Returns:
            Dictionary with token status information
        """
        credentials = self.get_credentials()
        if not credentials:
            return {"valid": False, "expired": True, "expiry": None, "needs_refresh": True}

        needs_refresh, expiry = self.check_token_expiration()

        return {
            "valid": credentials.valid,
            "expired": credentials.expired,
            "expiry": expiry.isoformat() if expiry else None,
            "needs_refresh": needs_refresh,
            "has_refresh_token": bool(credentials.refresh_token),
        }
