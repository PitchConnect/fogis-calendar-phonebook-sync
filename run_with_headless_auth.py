#!/usr/bin/env python3
"""
Wrapper script to run FOGIS Calendar Sync with headless authentication.

This script provides a simple way to run the calendar sync with automatic
re-authentication without modifying the main application.
"""

import json
import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config.json: {e}")
        return {}


def check_dependencies():
    """Check if all required files and dependencies are available."""
    required_files = [
        "config.json",
        "fogis_calendar_sync.py",
        "token_manager.py",
        "auth_server.py",
        "notification.py",
        "headless_auth.py",
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False

    # Check for credentials file
    if not os.path.exists("credentials.json"):
        logger.warning("credentials.json not found - you'll need this for Google authentication")

    return True


def setup_headless_monitoring():
    """Set up headless authentication monitoring."""
    try:
        from headless_auth import HeadlessAuthManager

        auth_manager = HeadlessAuthManager()

        # Check current token status
        token_status = auth_manager.get_token_status()
        logger.info(
            f"Token status: valid={token_status.get('valid', False)}, "
            f"needs_refresh={token_status.get('needs_refresh', True)}"
        )

        if token_status.get("needs_refresh", True):
            logger.info("Token needs refresh - starting headless authentication")

            # Get valid credentials (this will trigger auth flow if needed)
            credentials = auth_manager.get_valid_credentials()
            if not credentials:
                logger.error("Failed to get valid credentials")
                return None

        # Start background monitoring
        auth_manager.start_monitoring()
        logger.info("Started background token monitoring")

        return auth_manager

    except ImportError as e:
        logger.error(f"Failed to import headless auth modules: {e}")
        return None
    except Exception as e:
        logger.error(f"Error setting up headless monitoring: {e}")
        return None


def run_calendar_sync():
    """Run the main calendar sync application."""
    try:
        # Import and run the main sync function
        import subprocess

        logger.info("Starting FOGIS Calendar Sync...")

        # Run the main application
        result = subprocess.run(
            [sys.executable, "fogis_calendar_sync.py"], capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.info("Calendar sync completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"Calendar sync failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        logger.exception(f"Error running calendar sync: {e}")
        return False


def main():
    """Main function."""
    logger.info("🚀 Starting FOGIS Calendar Sync with Headless Authentication")
    logger.info("=" * 60)

    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        return 1

    # Set up headless authentication monitoring
    auth_manager = setup_headless_monitoring()
    if not auth_manager:
        logger.warning("⚠️  Headless authentication not available - running without it")
    else:
        logger.info("✅ Headless authentication monitoring active")

    try:
        # Run the calendar sync
        success = run_calendar_sync()

        if success:
            logger.info("✅ Calendar sync completed successfully")
            return 0
        else:
            logger.error("❌ Calendar sync failed")
            return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    finally:
        # Clean up
        if auth_manager:
            auth_manager.stop_monitoring()
            logger.info("Stopped background monitoring")


if __name__ == "__main__":
    sys.exit(main())
