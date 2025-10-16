import json
import logging
import os
import subprocess
import time
from typing import Dict, List, Union

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Import enhanced logging and error handling
from src.core import (
    CalendarSyncError,
    configure_logging,
    get_logger,
    handle_calendar_errors,
)

# Import Redis integration
from src.redis_integration import add_redis_to_calendar_app

# Import version information
from version import get_version

# Load environment variables from .env file
load_dotenv()

# Configure enhanced logging
configure_logging(
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    enable_console=os.environ.get("LOG_ENABLE_CONSOLE", "true").lower() == "true",
    enable_file=os.environ.get("LOG_ENABLE_FILE", "true").lower() == "true",
    enable_structured=os.environ.get("LOG_ENABLE_STRUCTURED", "true").lower() == "true",
    log_dir=os.environ.get("LOG_DIR", "logs"),
    log_file=os.environ.get("LOG_FILE", "fogis-calendar-phonebook-sync.log"),
)

app = Flask(__name__)

# Get enhanced logger
logger = get_logger(__name__, "app")

# Global Google Calendar service (initialized at startup)
calendar_service = None
people_service = None


def initialize_google_services():
    """Initialize Google Calendar and People API services at app startup."""
    global calendar_service, people_service

    try:
        # Load OAuth token
        token_path = os.environ.get(
            "GOOGLE_CALENDAR_TOKEN_FILE", "/app/credentials/tokens/calendar/token.json"
        )

        if not os.path.exists(token_path):
            logger.warning(f"OAuth token not found at {token_path}")
            return False

        # Load credentials
        with open(token_path, "r") as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )

        # Build services
        calendar_service = build("calendar", "v3", credentials=creds)
        people_service = build("people", "v1", credentials=creds)

        logger.info("✅ Google Calendar and People API services initialized")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize Google services: {e}")
        return False


# Initialize services at startup
initialize_google_services()


def calendar_sync_callback(data: Union[List[Dict], Dict]) -> bool:
    """
    Process match updates received from Redis.

    This callback is invoked by the Redis subscriber when match updates
    are received from the match-list-processor service.

    Supports both formats:
    - Enhanced Schema v2.0 (dict): {"matches": [...], "schema_version": "...", ...}
    - Legacy Schema v1.0 (list): [match1, match2, ...]

    Args:
        data: Either a dict (v2.0) or list (v1.0) containing match data

    Returns:
        bool: True if sync successful, False otherwise
    """
    try:
        if not calendar_service:
            logger.error("❌ Calendar service not initialized")
            return False

        # Handle both enriched dict and simple list formats
        if isinstance(data, dict):
            # Enhanced Schema v2.0 format
            matches = data.get("matches", [])
            schema_version = data.get("schema_version", "unknown")
            detailed_changes = data.get("detailed_changes", [])
            high_priority = data.get("high_priority", False)

            logger.info(
                f"🗓️ Processing {len(matches)} matches from Redis "
                f"(Schema v{schema_version}, {len(detailed_changes)} changes, "
                f"priority: {'HIGH' if high_priority else 'normal'})"
            )
        elif isinstance(data, list):
            # Legacy Schema v1.0 format (simple list)
            matches = data
            schema_version = "1.0"
            detailed_changes = []
            high_priority = False

            logger.info(
                f"🗓️ Processing {len(matches)} matches from Redis "
                f"(Legacy Schema v{schema_version})"
            )
        else:
            logger.error(f"❌ Unexpected data type: {type(data)}")
            return False

        if not matches:
            logger.info("📋 No matches to process")
            return True

        # Import calendar sync logic
        from fogis_calendar_sync import (
            find_event_by_match_id,
            generate_calendar_hash,
            sync_calendar,
        )

        # Process each match
        processed = 0
        failed = 0

        for match in matches:
            try:
                match_id = str(match["matchid"])

                # Create a minimal args object for sync_calendar
                class Args:
                    delete = False
                    fresh_sync = False
                    force_calendar = False
                    force_contacts = False
                    force_all = False

                args = Args()

                # Sync calendar event
                success = sync_calendar(match, calendar_service, args)

                if success:
                    processed += 1
                    logger.info(f"✅ Match {match_id}: Calendar sync successful")
                else:
                    failed += 1
                    logger.error(f"❌ Match {match_id}: Calendar sync failed")

            except Exception as e:
                failed += 1
                match_id = match.get("matchid", "unknown") if isinstance(match, dict) else "unknown"
                logger.error(f"❌ Error processing match {match_id}: {e}", exc_info=True)

        logger.info(f"📊 Redis sync complete: {processed} processed, {failed} failed")

        # Return True if at least some matches were processed successfully
        return processed > 0 or (processed == 0 and failed == 0)

    except Exception as e:
        logger.error(f"❌ Calendar sync callback failed: {e}", exc_info=True)
        return False


@app.route("/health", methods=["GET"])
@handle_calendar_errors("health_check", "health")
def health_check():
    """Optimized health check endpoint with minimal logging."""
    start_time = time.time()

    try:
        # Check if we can access the data directory
        if not os.path.exists("data"):
            logger.error("Data directory not accessible")
            return (
                jsonify({"status": "error", "message": "Data directory not accessible"}),
                500,
            )

        # Check if OAuth token exists and is readable
        # Use environment variable path if available, otherwise check multiple locations
        token_path = os.environ.get(
            "GOOGLE_CALENDAR_TOKEN_FILE", "/app/credentials/tokens/calendar/token.json"
        )
        logger.debug(f"Checking OAuth token at path: {token_path}")
        legacy_token_path = "/app/data/token.json"
        working_dir_token = "/app/token.json"

        token_found = False
        token_location = None

        # Check preferred location first (environment variable)
        if os.path.exists(token_path):
            token_found = True
            token_location = token_path
        # Check legacy data directory
        elif os.path.exists(legacy_token_path):
            token_found = True
            token_location = legacy_token_path
        # Check working directory (backward compatibility)
        elif os.path.exists(working_dir_token):
            token_found = True
            token_location = working_dir_token

        if not token_found:
            logger.warning(
                f"OAuth token not found in any checked locations: {[token_path, legacy_token_path, working_dir_token]}"
            )
            return (
                jsonify(
                    {
                        "status": "initializing",
                        "auth_status": "initializing",
                        "message": "OAuth token not found - service may be starting up",
                        "checked_locations": [
                            token_path,
                            legacy_token_path,
                            working_dir_token,
                        ],
                        "auth_url": "http://localhost:9083/authorize",
                        "note": "If this persists after 60 seconds, authentication may be required",
                    }
                ),
                200,
            )

        # Add any other critical checks here

        # Get version information
        version = get_version()

        # Get OAuth token expiry information if available
        oauth_info = {"status": "authenticated", "location": token_location}
        try:
            import json
            from datetime import datetime

            if os.path.exists(token_location):
                with open(token_location, "r") as f:
                    token_data = json.load(f)

                if "expiry" in token_data:
                    expiry_str = token_data["expiry"]
                    # Parse ISO format datetime
                    expiry_dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                    oauth_info["token_expiry"] = expiry_str
                    oauth_info["expires_in_hours"] = round(
                        (expiry_dt - datetime.now(expiry_dt.tzinfo)).total_seconds() / 3600,
                        1,
                    )

                if "refresh_token" in token_data:
                    oauth_info["has_refresh_token"] = bool(token_data["refresh_token"])

        except Exception as e:
            logging.debug(f"Could not parse OAuth token info: {e}")

        # Single optimized log entry
        duration = time.time() - start_time
        logger.info(f"✅ Health check OK ({duration:.3f}s)")

        return (
            jsonify(
                {
                    "status": "healthy",
                    "version": version,
                    "environment": os.environ.get("ENVIRONMENT", "development"),
                    "auth_status": oauth_info["status"],
                    "token_location": oauth_info["location"],
                    "oauth_info": oauth_info,
                }
            ),
            200,
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Health check FAILED ({duration:.3f}s): {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/sync", methods=["POST"])
@handle_calendar_errors("fogis_sync", "sync")
def sync_fogis():
    """Endpoint to trigger FOGIS calendar and contacts sync."""
    logger.info("FOGIS sync request received")
    try:
        # Get optional parameters from request
        data = request.get_json(silent=True) or {}
        delete_events = data.get("delete", False)

        # Build command
        cmd = ["python", "fogis_calendar_sync.py"]
        if delete_events:
            cmd.append("--delete")

        # Set environment variables for FOGIS credentials if provided
        env = os.environ.copy()
        if "username" in data and "password" in data:
            env["FOGIS_USERNAME"] = data["username"]
            env["FOGIS_PASSWORD"] = data["password"]

        # Run the sync script as a subprocess
        logger.info(f"Starting FOGIS sync process with command: {' '.join(cmd)}")
        process = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

        # Check if the process was successful
        if process.returncode == 0:
            # Check for errors in stderr even with success return code
            if process.stderr and ("ERROR" in process.stderr or "FAILED" in process.stderr.upper()):
                logger.warning(f"FOGIS sync completed with warnings/errors: {process.stderr}")
                return jsonify(
                    {
                        "status": "warning",
                        "message": "FOGIS sync completed with warnings",
                        "output": process.stdout,
                        "warnings": process.stderr,
                    }
                )
            else:
                logger.info("FOGIS sync completed successfully")
                return jsonify(
                    {
                        "status": "success",
                        "message": "FOGIS sync completed successfully",
                        "output": process.stdout,
                    }
                )

        logger.error(f"FOGIS sync failed with error: {process.stderr}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "FOGIS sync failed",
                    "error": process.stderr,
                    "output": process.stdout,
                }
            ),
            500,
        )

    except Exception as e:
        logger.exception("Error during FOGIS sync")
        return (
            jsonify({"status": "error", "message": f"Error during FOGIS sync: {str(e)}"}),
            500,
        )


# Initialize Redis integration
try:
    logger.info("🔗 Initializing Redis integration...")
    redis_integration = add_redis_to_calendar_app(app, calendar_sync_callback)
    logger.info("✅ Redis integration initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Redis integration: {e}")
    logger.warning("⚠️ Service will continue without Redis pub/sub functionality")


if __name__ == "__main__":
    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))

    logger.info(f"Starting FOGIS Calendar & Phonebook Sync service on {host}:{port}")
    logger.info(f"Version: {get_version()}")
    logger.info(f"Log level: {os.environ.get('LOG_LEVEL', 'INFO')}")

    app.run(host=host, port=port)
