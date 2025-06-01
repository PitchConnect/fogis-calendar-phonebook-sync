"""
Tests for the TokenManager class.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from token_manager import TokenManager


class TestTokenManager(unittest.TestCase):
    """Test cases for the TokenManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts"
            ],
            "TOKEN_REFRESH_BUFFER_DAYS": 6
        }

        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = os.path.join(self.temp_dir, "credentials.json")
        self.token_file = os.path.join(self.temp_dir, "token.json")

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if os.path.exists(self.credentials_file):
            os.remove(self.credentials_file)
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        os.rmdir(self.temp_dir)

    def test_init(self):
        """Test TokenManager initialization."""
        token_manager = TokenManager(
            self.config,
            self.credentials_file,
            self.token_file
        )

        self.assertEqual(token_manager.config, self.config)
        self.assertEqual(token_manager.credentials_file, self.credentials_file)
        self.assertEqual(token_manager.token_file, self.token_file)
        self.assertEqual(token_manager.scopes, self.config["SCOPES"])
        self.assertEqual(token_manager.refresh_buffer_days, 6)

    def test_get_credentials_no_token_file(self):
        """Test getting credentials when no token file exists."""
        token_manager = TokenManager(
            self.config,
            self.credentials_file,
            self.token_file
        )

        result = token_manager.get_credentials()
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
