#!/usr/bin/env python3
"""
Web-based authentication trigger service.

This creates a simple web interface that you can bookmark and visit
to restart the authentication process when you miss the 10-minute window.
"""

import json
import logging
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template_string, request

from headless_auth import HeadlessAuthManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
auth_manager = None

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>FOGIS Authentication Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .error { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .info { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
        button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background-color: #0056b3; }
        button.danger { background-color: #dc3545; }
        button.danger:hover { background-color: #c82333; }
        .token-info { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .refresh { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🔐 FOGIS Authentication Manager</h1>

    <div class="token-info">
        <h3>📊 Current Token Status</h3>
        <p><strong>Valid:</strong> {{ token_status.valid }}</p>
        <p><strong>Expired:</strong> {{ token_status.expired }}</p>
        <p><strong>Needs Refresh:</strong> {{ token_status.needs_refresh }}</p>
        {% if token_status.expiry %}
        <p><strong>Expires:</strong> {{ token_status.expiry }}</p>
        {% endif %}
        <p><strong>Has Refresh Token:</strong> {{ token_status.has_refresh_token }}</p>
        <p><strong>Last Updated:</strong> {{ current_time }}</p>
    </div>

    {% if token_status.valid and not token_status.needs_refresh %}
    <div class="status success">
        ✅ Token is valid and doesn't need refresh. Your FOGIS sync is working properly!
    </div>
    {% elif token_status.needs_refresh %}
    <div class="status warning">
        ⚠️ Token needs refresh. You should re-authenticate soon.
    </div>
    {% else %}
    <div class="status error">
        ❌ No valid token found. Authentication required.
    </div>
    {% endif %}

    <div class="refresh">
        <h3>🔄 Authentication Actions</h3>

        <form method="post" action="/restart-auth" style="display: inline;">
            <button type="submit" class="danger">🚀 Start New Authentication</button>
        </form>

        <button onclick="location.reload()">🔄 Refresh Status</button>

        <p><small>
            <strong>Note:</strong> Starting new authentication will send you a fresh email
            with a new 10-minute authentication window.
        </small></p>
    </div>

    <div class="status info">
        <h4>💡 How to Use This Page</h4>
        <ul>
            <li><strong>Bookmark this page</strong> for easy access when you need to re-authenticate</li>
            <li><strong>Click "Start New Authentication"</strong> if you missed the 10-minute window</li>
            <li><strong>Check your email</strong> for the new authentication link</li>
            <li><strong>Complete authentication</strong> within 10 minutes of receiving the email</li>
        </ul>
    </div>

    <hr>
    <p><small>FOGIS Calendar Sync - Headless Authentication Manager</small></p>
</body>
</html>
"""


@app.route("/")
def index():
    """Main authentication management page."""
    global auth_manager

    if not auth_manager:
        auth_manager = HeadlessAuthManager()

    token_status = auth_manager.get_token_status()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template_string(
        HTML_TEMPLATE, token_status=token_status, current_time=current_time
    )


@app.route("/restart-auth", methods=["POST"])
def restart_auth():
    """Restart the authentication process."""
    global auth_manager

    try:
        if not auth_manager:
            auth_manager = HeadlessAuthManager()

        logger.info("Web interface triggered authentication restart")

        # Start authentication in background thread to avoid blocking the web response
        def auth_thread():
            try:
                success = auth_manager.force_refresh()
                if success:
                    logger.info("Web-triggered authentication completed successfully")
                else:
                    logger.error("Web-triggered authentication failed")
            except Exception as e:
                logger.exception(f"Error in web-triggered authentication: {e}")

        thread = threading.Thread(target=auth_thread)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "success": True,
                "message": "Authentication process started! Check your email for the new authentication link.",
            }
        )

    except Exception as e:
        logger.exception(f"Error starting authentication: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/status")
def status():
    """API endpoint for token status."""
    global auth_manager

    if not auth_manager:
        auth_manager = HeadlessAuthManager()

    token_status = auth_manager.get_token_status()
    return jsonify(token_status)


def main():
    """Run the web authentication trigger service."""
    print("🌐 Starting FOGIS Authentication Web Manager")
    print("=" * 50)
    print("📱 Access at: http://localhost:8090")
    print("🔖 Bookmark this URL for easy authentication restarts!")
    print("=" * 50)

    app.run(host="0.0.0.0", port=8090, debug=False)


if __name__ == "__main__":
    main()
