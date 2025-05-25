"""
Authentication Server for Headless Google OAuth

This module provides a lightweight web server to handle OAuth callbacks
in headless server environments.
"""

import logging
import secrets
import threading
import time
from typing import Dict, Optional

from flask import Flask, request, jsonify
from werkzeug.serving import make_server

logger = logging.getLogger(__name__)


class AuthServer:
    """Lightweight authentication server for handling OAuth callbacks."""
    
    def __init__(self, config: Dict, token_manager):
        """
        Initialize the authentication server.
        
        Args:
            config: Configuration dictionary
            token_manager: TokenManager instance
        """
        self.config = config
        self.token_manager = token_manager
        self.host = config.get("AUTH_SERVER_HOST", "localhost")
        self.port = config.get("AUTH_SERVER_PORT", 8080)
        self.state = None
        self.server = None
        self.server_thread = None
        self.auth_completed = False
        self.auth_success = False
        self.timeout_seconds = 600  # 10 minutes
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.WARNING)  # Reduce Flask logging
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for the authentication server."""
        
        @self.app.route('/callback')
        def callback():
            """Handle OAuth callback."""
            try:
                # Verify state parameter for security
                received_state = request.args.get('state')
                if received_state != self.state:
                    logger.error("Invalid state parameter in callback")
                    return jsonify({
                        "error": "Invalid state parameter",
                        "success": False
                    }), 400
                
                # Check for error in callback
                error = request.args.get('error')
                if error:
                    logger.error(f"OAuth error: {error}")
                    self.auth_completed = True
                    self.auth_success = False
                    return jsonify({
                        "error": f"OAuth error: {error}",
                        "success": False
                    }), 400
                
                # Get authorization code
                auth_code = request.args.get('code')
                if not auth_code:
                    logger.error("No authorization code received")
                    self.auth_completed = True
                    self.auth_success = False
                    return jsonify({
                        "error": "No authorization code received",
                        "success": False
                    }), 400
                
                # Complete the auth flow
                authorization_response = request.url
                success = self.token_manager.complete_auth_flow(authorization_response)
                
                self.auth_completed = True
                self.auth_success = success
                
                if success:
                    logger.info("Authentication completed successfully")
                    return """
                    <html>
                    <head><title>Authentication Successful</title></head>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h1 style="color: green;">✅ Authentication Successful!</h1>
                        <p>You have successfully authenticated with Google.</p>
                        <p>You can now close this window and return to your application.</p>
                        <script>
                            setTimeout(function() {
                                window.close();
                            }, 3000);
                        </script>
                    </body>
                    </html>
                    """
                else:
                    logger.error("Failed to complete authentication flow")
                    return """
                    <html>
                    <head><title>Authentication Failed</title></head>
                    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                        <h1 style="color: red;">❌ Authentication Failed</h1>
                        <p>There was an error completing the authentication process.</p>
                        <p>Please check the application logs and try again.</p>
                    </body>
                    </html>
                    """, 500
                    
            except Exception as e:
                logger.exception("Exception in callback handler")
                self.auth_completed = True
                self.auth_success = False
                return jsonify({
                    "error": f"Internal error: {str(e)}",
                    "success": False
                }), 500
        
        @self.app.route('/health')
        def health():
            """Health check endpoint."""
            return jsonify({
                "status": "running",
                "auth_completed": self.auth_completed,
                "auth_success": self.auth_success
            })
    
    def start(self) -> str:
        """
        Start the authentication server.
        
        Returns:
            Authorization URL for user to visit
        """
        # Generate secure state parameter
        self.state = secrets.token_urlsafe(32)
        
        # Reset auth status
        self.auth_completed = False
        self.auth_success = False
        
        # Create server
        self.server = make_server(
            self.host, 
            self.port, 
            self.app, 
            threaded=True
        )
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"Authentication server started on {self.host}:{self.port}")
        
        # Get authorization URL from token manager
        auth_url = self.token_manager.initiate_auth_flow()
        
        # Add state parameter to URL
        separator = "&" if "?" in auth_url else "?"
        auth_url_with_state = f"{auth_url}{separator}state={self.state}"
        
        return auth_url_with_state
    
    def wait_for_auth(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for authentication to complete.
        
        Args:
            timeout: Timeout in seconds (default: self.timeout_seconds)
            
        Returns:
            True if authentication successful, False otherwise
        """
        timeout = timeout or self.timeout_seconds
        start_time = time.time()
        
        while not self.auth_completed and (time.time() - start_time) < timeout:
            time.sleep(1)
        
        if not self.auth_completed:
            logger.warning(f"Authentication timed out after {timeout} seconds")
            return False
        
        return self.auth_success
    
    def stop(self):
        """Stop the authentication server."""
        if self.server:
            logger.info("Stopping authentication server")
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=5)
            self.server = None
            self.server_thread = None
    
    def get_auth_url(self) -> Optional[str]:
        """
        Get the current authorization URL.
        
        Returns:
            Authorization URL or None if server not started
        """
        if not self.server or not self.state:
            return None
        
        base_url = f"http://{self.host}:{self.port}/callback"
        return f"Please visit: {base_url} (with proper OAuth flow)"
