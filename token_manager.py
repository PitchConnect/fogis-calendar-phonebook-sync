"""Token Manager Module.

This module handles Google API token management, including tracking token expiration,
proactive token refresh, and token storage.
"""

import datetime
import json
import logging
import os
from typing import Dict, Optional, Tuple, Union

import google.auth
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = "token.json"
TOKEN_METADATA_FILE = "token_metadata.json"
# Default buffer time (in days) before token expiration to trigger refresh
DEFAULT_REFRESH_BUFFER_DAYS = 1


def load_token() -> Optional[Credentials]:
    """Load token from token file.

    Returns:
        Optional[Credentials]: The loaded credentials or None if loading fails
    """
    if not os.path.exists(TOKEN_FILE):
        logger.info("Token file does not exist: %s", TOKEN_FILE)
        return None

    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)

        # Load config to get scopes
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            scopes = config.get("SCOPES", [])

        creds = Credentials.from_authorized_user_info(token_data, scopes)
        logger.info("Successfully loaded credentials from %s", TOKEN_FILE)
        return creds
    except Exception as e:
        logger.error("Error loading credentials from %s: %s", TOKEN_FILE, e)
        return None


def save_token(creds: Credentials) -> bool:
    """Save token to token file and update metadata.

    Args:
        creds (Credentials): The credentials to save

    Returns:
        bool: True if saving was successful, False otherwise
    """
    try:
        # Save the token
        token_json = creds.to_json()
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token_json)

        # Update metadata
        metadata = {
            "token_type": "google_oauth",
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": get_token_expiry(creds).isoformat() if creds.expiry else None,
            "scopes": creds.scopes,
        }

        with open(TOKEN_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved credentials to %s and updated metadata", TOKEN_FILE)
        return True
    except Exception as e:
        logger.error("Error saving credentials to %s: %s", TOKEN_FILE, e)
        return False


def get_token_expiry(creds: Credentials) -> datetime.datetime:
    """Get the expiry datetime of the token.

    Args:
        creds (Credentials): The credentials to check

    Returns:
        datetime.datetime: The expiry datetime
    """
    if not creds.expiry:
        # If no expiry is set, assume it's 7 days from now (for refresh tokens in test mode)
        return datetime.datetime.now() + datetime.timedelta(days=7)
    return creds.expiry


def is_token_expiring_soon(
    creds: Credentials, buffer_days: int = DEFAULT_REFRESH_BUFFER_DAYS
) -> bool:
    """Check if the token is expiring soon.

    Args:
        creds (Credentials): The credentials to check
        buffer_days (int): Number of days before expiration to consider "expiring soon"

    Returns:
        bool: True if the token is expiring within the buffer period, False otherwise
    """
    if not creds or not creds.valid:
        return True

    if creds.expiry:
        expiry = creds.expiry
    else:
        # Check metadata for expiry if not in credentials
        try:
            with open(TOKEN_METADATA_FILE, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                expiry_str = metadata.get("expires_at")
                if expiry_str:
                    expiry = datetime.datetime.fromisoformat(expiry_str)
                else:
                    # Default to 7 days from creation if no expiry in metadata
                    created_at_str = metadata.get("created_at")
                    if created_at_str:
                        created_at = datetime.datetime.fromisoformat(created_at_str)
                        expiry = created_at + datetime.timedelta(days=7)
                    else:
                        # If no creation date, assume it's expiring soon
                        return True
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.warning("Error reading token metadata: %s. Assuming token is expiring soon.", e)
            return True

    buffer_timedelta = datetime.timedelta(days=buffer_days)
    return datetime.datetime.now() + buffer_timedelta >= expiry


def refresh_token(creds: Credentials) -> Tuple[Optional[Credentials], bool]:
    """Attempt to refresh the token.

    Args:
        creds (Credentials): The credentials to refresh

    Returns:
        Tuple[Optional[Credentials], bool]: The refreshed credentials and a success flag
    """
    if not creds:
        logger.error("Cannot refresh None credentials")
        return None, False

    if not creds.refresh_token:
        logger.error("Credentials do not have a refresh token")
        return creds, False

    try:
        logger.info("Attempting to refresh token")
        creds.refresh(Request())
        logger.info("Token refreshed successfully")

        # Save the refreshed token
        if save_token(creds):
            return creds, True
        else:
            logger.warning("Token refreshed but failed to save")
            return creds, True  # Still return True since refresh succeeded
    except RefreshError as e:
        logger.error("Error refreshing token (RefreshError): %s", e)
        return creds, False
    except Exception as e:
        logger.error("Error refreshing token: %s", e)
        return creds, False


def check_and_refresh_token(
    creds: Optional[Credentials] = None, buffer_days: int = DEFAULT_REFRESH_BUFFER_DAYS
) -> Tuple[Optional[Credentials], bool]:
    """Check if token needs refreshing and refresh if needed.

    Args:
        creds (Optional[Credentials]): The credentials to check, or None to load from file
        buffer_days (int): Number of days before expiration to trigger refresh

    Returns:
        Tuple[Optional[Credentials], bool]: The (possibly refreshed) credentials and a success flag
    """
    if creds is None:
        creds = load_token()
        if creds is None:
            return None, False

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            return refresh_token(creds)
        else:
            logger.warning("Token is invalid and cannot be refreshed")
            return creds, False

    if is_token_expiring_soon(creds, buffer_days):
        logger.info("Token is expiring soon, attempting to refresh")
        return refresh_token(creds)

    logger.info("Token is valid and not expiring soon")
    return creds, True


def get_token_info() -> Dict[str, Union[str, bool, int]]:
    """Get information about the current token.

    Returns:
        Dict[str, Union[str, bool, int]]: Information about the token
    """
    creds = load_token()
    result = {
        "exists": creds is not None,
        "valid": False,
        "expired": True,
        "has_refresh_token": False,
        "days_until_expiry": 0,
        "scopes": [],
    }

    if creds:
        result["valid"] = creds.valid
        result["expired"] = creds.expired if hasattr(creds, "expired") else True
        result["has_refresh_token"] = bool(creds.refresh_token)
        result["scopes"] = creds.scopes

        if creds.expiry:
            days = (creds.expiry - datetime.datetime.now()).days
            result["days_until_expiry"] = max(0, days)

    return result


def delete_token() -> bool:
    """Delete the token file.

    Returns:
        bool: True if deletion was successful or file didn't exist, False otherwise
    """
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            logger.info("Deleted token file: %s", TOKEN_FILE)

        if os.path.exists(TOKEN_METADATA_FILE):
            os.remove(TOKEN_METADATA_FILE)
            logger.info("Deleted token metadata file: %s", TOKEN_METADATA_FILE)

        return True
    except Exception as e:
        logger.error("Error deleting token files: %s", e)
        return False
