import logging
import os
import subprocess

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Import enhanced logging and error handling
from src.core import (
    CalendarSyncError,
    configure_logging,
    get_logger,
    handle_calendar_errors,
)

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


@app.route("/health", methods=["GET"])
@handle_calendar_errors("health_check", "health")
def health_check():
    """Health check endpoint for Docker healthcheck."""
    logger.info("Health check requested")
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
        logging.exception("Health check failed")
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


if __name__ == "__main__":
    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))

    logger.info(f"Starting FOGIS Calendar & Phonebook Sync service on {host}:{port}")
    logger.info(f"Version: {get_version()}")
    logger.info(f"Log level: {os.environ.get('LOG_LEVEL', 'INFO')}")

    app.run(host=host, port=port)
