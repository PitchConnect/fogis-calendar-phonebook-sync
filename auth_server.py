"""Authentication Server Module.

This module provides a lightweight web server for handling OAuth callbacks
and managing the authentication flow in headless mode.
"""

import json
import logging
import os
import secrets
import threading
import time
import webbrowser
from typing import Dict, Optional, Tuple, Union

import google.auth
from flask import Flask, redirect, request, url_for
from google_auth_oauthlib.flow import Flow
from werkzeug.serving import make_server

import notification
import token_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global variables
AUTH_SERVER = None
AUTH_SERVER_THREAD = None
AUTH_FLOW = None
AUTH_STATE = None
AUTH_SUCCESS = False
AUTH_TIMEOUT = 600  # 10 minutes in seconds


def load_config() -> Dict[str, Union[str, int]]:
    """Load configuration from config.json.

    Returns:
        Dict[str, Union[str, int]]: Configuration dictionary
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Error loading config: %s", e)
        return {}


def create_auth_server() -> Flask:
    """Create a Flask server for handling OAuth callbacks.

    Returns:
        Flask: The Flask application
    """
    app = Flask(__name__)

    @app.route("/")
    def index():
        """Root endpoint that redirects to the auth endpoint."""
        return redirect(url_for("start_auth"))

    @app.route("/auth")
    def start_auth():
        """Start the OAuth flow."""
        global AUTH_FLOW, auth_state

        if not auth_flow:
            return "Authentication server is not properly initialized.", 500

        # Generate a state parameter for CSRF protection
        auth_state = secrets.token_urlsafe(32)

        # Create the authorization URL
        auth_url, _ = auth_flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=auth_state,
            prompt="consent",  # Force consent screen to ensure we get a refresh token
        )

        # Redirect to the authorization URL
        return redirect(auth_url)

    @app.route("/oauth2callback")
    def oauth2callback():
        """Handle the OAuth callback."""
        global AUTH_FLOW, auth_state, auth_success

        if not auth_flow:
            return "Authentication server is not properly initialized.", 500

        # Verify state parameter to prevent CSRF
        state = request.args.get("state", "")
        if state != auth_state:
            return "Invalid state parameter. Authentication failed.", 400

        try:
            # Exchange authorization code for credentials
            auth_flow.fetch_token(authorization_response=request.url)
            credentials = auth_flow.credentials

            # Save the credentials
            token_manager.save_token(credentials)

            auth_success = True

            return """
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        text-align: center;
                    }
                    .success {
                        color: green;
                        font-size: 24px;
                        margin-bottom: 20px;
                    }
                    .info {
                        margin-bottom: 15px;
                    }
                </style>
            </head>
            <body>
                <div class="success">Authentication Successful!</div>
                <div class="info">You have successfully authenticated FOGIS Calendar Sync.</div>
                <div class="info">You can now close this window and return to the application.</div>
            </body>
            </html>
            """
        except Exception as e:
            logger.error("Error during OAuth callback: %s", e)
            return f"Authentication failed: {str(e)}", 400

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return {"status": "healthy"}, 200

    return app


class ServerThread(threading.Thread):
    """Thread for running the Flask server."""

    def __init__(self, app, host, port):
        """Initialize the server thread.

        Args:
            app (Flask): The Flask application
            host (str): The host to bind to
            port (int): The port to bind to
        """
        threading.Thread.__init__(self)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        """Run the server."""
        logger.info("Starting authentication server")
        self.server.serve_forever()

    def shutdown(self):
        """Shutdown the server."""
        logger.info("Shutting down authentication server")
        self.server.shutdown()


def start_auth_server() -> Tuple[str, int]:
    """Start the authentication server.

    Returns:
        Tuple[str, int]: The server URL and port
    """
    global AUTH_SERVER, auth_server_thread, auth_flow, auth_success

    config = load_config()
    host = config.get("AUTH_SERVER_HOST", "localhost")
    port = config.get("AUTH_SERVER_PORT", 8080)

    # Create the Flask app
    auth_server = create_auth_server()

    # Start the server in a separate thread
    auth_server_thread = ServerThread(auth_server, host, port)
    auth_server_thread.daemon = True
    auth_server_thread.start()

    # Reset auth success flag
    auth_success = False

    logger.info("Authentication server started at http://%s:%s", host, port)
    return host, port


def stop_auth_server():
    """Stop the authentication server."""
    global AUTH_SERVER_thread

    if auth_server_thread:
        auth_server_thread.shutdown()
        auth_server_thread.join()
        auth_server_thread = None
        logger.info("Authentication server stopped")


def initialize_oauth_flow() -> bool:
    """Initialize the OAuth flow.

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global AUTH_FLOW

    config = load_config()
    credentials_file = config.get("CREDENTIALS_FILE", "credentials.json")
    scopes = config.get("SCOPES", [])

    if not os.path.exists(credentials_file):
        logger.error("Credentials file not found: %s", credentials_file)
        return False

    try:
        # Create the flow using the client secrets file
        auth_flow = Flow.from_client_secrets_file(
            credentials_file,
            scopes=scopes,
            redirect_uri=f"http://{config.get('AUTH_SERVER_HOST', 'localhost')}:{config.get('AUTH_SERVER_PORT', 8080)}/oauth2callback",
        )

        logger.info("OAuth flow initialized successfully")
        return True
    except Exception as e:
        logger.error("Error initializing OAuth flow: %s", e)
        return False


def get_auth_url() -> str:
    """Get the authentication URL.

    Returns:
        str: The authentication URL
    """
    config = load_config()
    host = config.get("AUTH_SERVER_HOST", "localhost")
    port = config.get("AUTH_SERVER_PORT", 8080)

    return f"http://{host}:{port}/auth"


def wait_for_auth(timeout_seconds: int = AUTH_TIMEOUT) -> bool:
    """Wait for authentication to complete.

    Args:
        timeout_seconds (int): Maximum time to wait in seconds

    Returns:
        bool: True if authentication was successful, False otherwise
    """
    global AUTH_SUCCESS

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if auth_success:
            return True
        time.sleep(1)

    logger.warning("Authentication timed out after %s seconds", timeout_seconds)
    return False


def start_headless_auth() -> bool:
    """Start the headless authentication process.

    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        # Start the authentication server
        _host, _port = start_auth_server()

        # Initialize the OAuth flow
        if not initialize_oauth_flow():
            stop_auth_server()
            return False

        # Get the authentication URL
        auth_url = get_auth_url()

        # Send notification with the authentication URL
        notification.send_notification(auth_url)

        # Wait for authentication to complete
        success = wait_for_auth()

        # Stop the authentication server
        stop_auth_server()

        return success
    except Exception as e:
        logger.error("Error during headless authentication: %s", e)
        stop_auth_server()
        return False


def check_and_refresh_auth() -> bool:
    """Check if authentication is needed and refresh if necessary.

    Returns:
        bool: True if authentication is valid, False otherwise
    """
    # Load the token
    creds = token_manager.load_token()

    # If no token exists or it's invalid and can't be refreshed, start headless auth
    if not creds or (
        not creds.valid
        and (not creds.refresh_token or not token_manager.is_token_expiring_soon(creds))
    ):
        logger.info("No valid token found, starting headless authentication")
        return start_headless_auth()

    # If token is expiring soon, try to refresh it
    if token_manager.is_token_expiring_soon(creds):
        logger.info("Token is expiring soon, attempting to refresh")
        creds, success = token_manager.refresh_token(creds)

        # If refresh failed, start headless auth
        if not success:
            logger.info("Token refresh failed, starting headless authentication")
            return start_headless_auth()

        return True

    # Token is valid and not expiring soon
    return True
