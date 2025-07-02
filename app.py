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
            return jsonify({"status": "error", "message": "Data directory not accessible"}), 500

        # Check if token.json exists and is readable
        if not os.path.exists("/app/data/token.json"):
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "token.json not found, may need authentication",
                    }
                ),
                200,
            )

        # Add any other critical checks here

        # Get version information
        version = get_version()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "version": version,
                    "environment": os.environ.get("ENVIRONMENT", "development"),
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
        return jsonify({"status": "error", "message": f"Error during FOGIS sync: {str(e)}"}), 500


if __name__ == "__main__":
    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))
    app.run(host=host, port=port)
