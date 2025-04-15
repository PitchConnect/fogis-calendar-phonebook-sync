"""Version information for FogisCalendarPhoneBookSync."""

import os

# Default version if not set during build
VERSION = os.environ.get("VERSION", "dev")


def get_version():
    """Return the current version of the application."""
    return VERSION
