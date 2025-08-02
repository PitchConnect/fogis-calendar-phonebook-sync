"""
FOGIS API Client Service

A containerized REST API wrapper around the FOGIS API client library.
This service provides HTTP endpoints for accessing FOGIS functionality
in a microservices architecture.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from fogis_api_client import FogisApiClient, MatchListFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global API client instance (will be initialized on first use)
_api_client: Optional[FogisApiClient] = None


def get_api_client() -> FogisApiClient:
    """Get or create the FOGIS API client instance."""
    global _api_client
    if _api_client is None:
        username = os.environ.get("FOGIS_USERNAME")
        password = os.environ.get("FOGIS_PASSWORD")

        if not username or not password:
            raise ValueError("FOGIS_USERNAME and FOGIS_PASSWORD environment variables are required")

        _api_client = FogisApiClient(username, password)
        logger.info("FOGIS API client initialized")

    return _api_client


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for container orchestration."""
    try:
        # Basic health check
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.environ.get("VERSION", "dev"),
            "service": "fogis-api-client",
        }

        # Optional: Test API client connection if credentials are available
        if os.environ.get("FOGIS_USERNAME") and os.environ.get("FOGIS_PASSWORD"):
            try:
                client = get_api_client()
                # Simple connection test - verify client can be created
                if client:
                    health_data["api_connection"] = "available"
                else:
                    health_data["api_connection"] = "unavailable"
            except Exception as e:
                logger.warning(f"API connection test failed: {e}")
                health_data["api_connection"] = "unavailable"
                health_data["api_error"] = str(e)
        else:
            health_data["api_connection"] = "not_configured"

        return jsonify(health_data), 200

    except Exception as e:
        logger.exception("Health check failed")
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                }
            ),
            500,
        )


@app.route("/api/matches", methods=["GET"])
def get_matches():
    """Get match list from FOGIS API."""
    try:
        client = get_api_client()

        # Get query parameters
        team_id = request.args.get("team_id")
        season = request.args.get("season")
        match_type = request.args.get("match_type")

        # Create filter if parameters provided
        filter_params = {}
        if team_id:
            filter_params["team_id"] = team_id
        if season:
            filter_params["season"] = season
        if match_type:
            filter_params["match_type"] = match_type

        # Get matches
        if filter_params:
            match_filter = MatchListFilter(**filter_params)
            matches = client.get_matches(match_filter)
        else:
            matches = client.get_matches()

        return (
            jsonify(
                {
                    "status": "success",
                    "data": matches,
                    "count": len(matches) if matches else 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "service_configuration_error",
                    "message": str(e),
                }
            ),
            500,
        )

    except Exception as e:
        logger.exception("Error fetching matches")
        return (
            jsonify({"status": "error", "error": "api_error", "message": str(e)}),
            500,
        )


@app.route("/api/teams", methods=["GET"])
def get_teams():
    """Get team list from FOGIS API."""
    try:
        client = get_api_client()
        teams = client.get_teams()

        return (
            jsonify(
                {
                    "status": "success",
                    "data": teams,
                    "count": len(teams) if teams else 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "service_configuration_error",
                    "message": str(e),
                }
            ),
            500,
        )

    except Exception as e:
        logger.exception("Error fetching teams")
        return (
            jsonify({"status": "error", "error": "api_error", "message": str(e)}),
            500,
        )


@app.route("/api/info", methods=["GET"])
def get_service_info():
    """Get service information and capabilities."""
    return (
        jsonify(
            {
                "service": "fogis-api-client",
                "version": os.environ.get("VERSION", "dev"),
                "description": "Containerized FOGIS API client for microservices architecture",
                "endpoints": {
                    "/health": "Health check endpoint",
                    "/api/matches": "Get match list (supports team_id, season, match_type query params)",
                    "/api/teams": "Get team list",
                    "/api/info": "Service information",
                },
                "environment": {
                    "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                    "configured": bool(
                        os.environ.get("FOGIS_USERNAME") and os.environ.get("FOGIS_PASSWORD")
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
        200,
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return (
        jsonify(
            {
                "status": "error",
                "error": "not_found",
                "message": "Endpoint not found",
                "available_endpoints": [
                    "/health",
                    "/api/matches",
                    "/api/teams",
                    "/api/info",
                ],
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.exception("Internal server error")
    return (
        jsonify(
            {
                "status": "error",
                "error": "internal_server_error",
                "message": "An internal error occurred",
            }
        ),
        500,
    )


if __name__ == "__main__":
    # Configuration
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger.info(f"Starting FOGIS API Client Service on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Version: {os.environ.get('VERSION', 'dev')}")

    app.run(host=host, port=port, debug=debug)
