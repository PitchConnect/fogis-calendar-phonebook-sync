import datetime
import json
import os
import subprocess
import time

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from flask import Flask, jsonify, request

import metrics
from logger import get_logger

# Import custom modules
from logging_config import add_request_context_to_logs, configure_logging

# Load environment variables from .env file
load_dotenv()

# Configure logging early in application startup
configure_logging(log_level="INFO", json_format=True)

# Get a logger for this module
logger = get_logger(__name__)

app = Flask(__name__)

# Initialize metrics
metrics.init_metrics(app)


@app.route("/health", methods=["GET"])
def health_check():
    """Enhanced health check endpoint with metrics."""
    try:
        # Add request context to logs
        request_id = add_request_context_to_logs().get("request_id")
        log = get_logger(__name__).bind(request_id=request_id, endpoint="/health")

        start_time = time.time()
        log.info("Health check started")

        # Basic checks
        checks = {
            "data_directory": os.path.exists("data"),
            "token_file": os.path.exists("token.json"),
            "config_file": os.path.exists("config.json"),
        }

        # Determine overall status
        status = "healthy" if all(checks.values()) else "unhealthy"
        if not checks["token_file"]:
            status = "warning"  # Still operational but needs attention

        # Get metrics
        metrics_data = {
            "uptime": time.time() - app.start_time if hasattr(app, "start_time") else 0,
            "api_latency": getattr(app, "last_api_latency", 0),
            "error_rate": getattr(app, "error_rate", 0),
        }

        # Track API latency for health check
        elapsed = time.time() - start_time
        metrics.track_api_latency("health", elapsed)

        response = {
            "status": status,
            "version": os.environ.get("APP_VERSION", "1.0.0"),
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "checks": checks,
            "metrics": metrics_data,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "request_id": request_id,
        }

        log.info("Health check completed", status=status, elapsed_ms=elapsed * 1000)

        return jsonify(response), 200 if status != "unhealthy" else 503
    except Exception as e:
        logger.exception("Health check failed", error=str(e))
        metrics.track_error("health_check")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/sync", methods=["POST"])
def sync_fogis():
    """Endpoint to trigger FOGIS calendar and contacts sync."""
    # Add request context to logs
    request_id = add_request_context_to_logs().get("request_id")
    log = get_logger(__name__).bind(request_id=request_id, endpoint="/sync")

    # Use metrics context manager to track active syncs
    with metrics.SyncOperation():
        try:
            start_time = time.time()

            # Get optional parameters from request
            data = request.get_json(silent=True) or {}
            delete_events = data.get("delete", False)
            download_only = data.get("download", False)

            # Log the request with structured context
            log.info(
                "Starting FOGIS sync",
                delete_events=delete_events,
                download_only=download_only,
                has_credentials="username" in data and "password" in data,
            )

            # Build command
            cmd = ["python", "fogis_calendar_sync.py"]
            if delete_events:
                cmd.append("--delete")
            if download_only:
                cmd.append("--download")

            # Set environment variables for FOGIS credentials if provided
            env = os.environ.copy()
            env["REQUEST_ID"] = request_id  # Pass request ID to subprocess

            if "username" in data and "password" in data:
                env["FOGIS_USERNAME"] = data["username"]
                env["FOGIS_PASSWORD"] = data["password"]

            # Run the sync script as a subprocess
            process = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

            # Calculate elapsed time
            elapsed = time.time() - start_time

            # Track API latency
            metrics.track_api_latency("sync", elapsed)

            # Check if the process was successful
            if process.returncode == 0:
                log.info(
                    "FOGIS sync completed successfully",
                    elapsed_ms=elapsed * 1000,
                    output_length=len(process.stdout),
                )

                # Track successful sync
                metrics.track_sync("success", "calendar_contacts")

                return jsonify(
                    {
                        "status": "success",
                        "message": "FOGIS sync completed successfully",
                        "output": process.stdout,
                        "elapsed_seconds": elapsed,
                        "request_id": request_id,
                    }
                )

            # Handle failure
            log.error(
                "FOGIS sync failed",
                elapsed_ms=elapsed * 1000,
                error=process.stderr,
                return_code=process.returncode,
            )

            # Track failed sync
            metrics.track_sync("failure", "calendar_contacts")
            metrics.track_error("sync_process")

            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "FOGIS sync failed",
                        "error": process.stderr,
                        "output": process.stdout,
                        "elapsed_seconds": elapsed,
                        "request_id": request_id,
                    }
                ),
                500,
            )

        except Exception as e:
            log.exception("Error during FOGIS sync", error=str(e))
            metrics.track_error("sync_exception")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Error during FOGIS sync: {str(e)}",
                        "request_id": request_id,
                    }
                ),
                500,
            )


# Add a metrics endpoint
@app.route("/metrics", methods=["GET"])
def metrics_endpoint():
    """Prometheus metrics endpoint.

    This endpoint is automatically handled by PrometheusMetrics.
    We just define it here for documentation purposes.
    """


if __name__ == "__main__":
    # Record application start time for uptime tracking
    app.start_time = time.time()

    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))

    # Log application startup
    logger.info(
        "Starting application",
        host=host,
        port=port,
        environment=os.environ.get("ENVIRONMENT", "development"),
        version=os.environ.get("APP_VERSION", "1.0.0"),
    )

    app.run(host=host, port=port)
