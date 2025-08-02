import logging
import os
import subprocess

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Import version information
from version import get_version

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker healthcheck."""
    try:
        # Check if we can access the data directory
        if not os.path.exists("data"):
            return (
                jsonify({"status": "error", "message": "Data directory not accessible"}),
                500,
            )

        # Check if OAuth token exists and is readable
        # Use environment variable path if available, otherwise check multiple locations
        token_path = os.environ.get(
            "GOOGLE_CALENDAR_TOKEN_FILE", "/app/credentials/tokens/calendar/token.json"
        )
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
def sync_fogis():
    """Endpoint to trigger FOGIS calendar and contacts sync."""
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
        logging.info("Starting FOGIS sync process")
        process = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

        # Check if the process was successful
        if process.returncode == 0:
            # Check for errors in stderr even with success return code
            if process.stderr and ("ERROR" in process.stderr or "FAILED" in process.stderr.upper()):
                logging.warning("FOGIS sync completed with warnings/errors: %s", process.stderr)
                return jsonify(
                    {
                        "status": "warning",
                        "message": "FOGIS sync completed with warnings",
                        "output": process.stdout,
                        "warnings": process.stderr,
                    }
                )
            else:
                logging.info("FOGIS sync completed successfully")
                return jsonify(
                    {
                        "status": "success",
                        "message": "FOGIS sync completed successfully",
                        "output": process.stdout,
                    }
                )

        logging.error("FOGIS sync failed with error: %s", process.stderr)
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
        logging.exception("Error during FOGIS sync")
        return (
            jsonify({"status": "error", "message": f"Error during FOGIS sync: {str(e)}"}),
            500,
        )


if __name__ == "__main__":
    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))
    app.run(host=host, port=port)
