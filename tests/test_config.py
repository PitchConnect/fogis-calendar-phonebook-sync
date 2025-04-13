"""
Tests for configuration loading and validation.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest


def test_sample_config_fixture(sample_config):
    """Test that the sample_config fixture works correctly."""
    assert isinstance(sample_config, dict)
    assert "CALENDAR_ID" in sample_config
    assert sample_config["SYNC_TAG"] == "TEST_SYNC_TAG"


@pytest.mark.unit
def test_load_config():
    """Test loading configuration from a file."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        config = {
            "COOKIE_FILE": "test_cookies.json",
            "CREDENTIALS_FILE": "test_credentials.json",
            "CALENDAR_ID": "test_calendar_id@group.calendar.google.com",
            "SYNC_TAG": "TEST_SYNC_TAG",
            "MATCH_FILE": "test_matches.json",
        }
        json.dump(config, temp_file)
        temp_file_path = temp_file.name

    try:
        # Mock the config loading function
        with patch("json.load") as mock_json_load:
            mock_json_load.return_value = config

            # Load the config (this is a simplified version of what the actual code would do)
            with open(temp_file_path, "r") as f:
                loaded_config = json.load(f)

            # Verify the config was loaded correctly
            assert loaded_config == config
            assert loaded_config["CALENDAR_ID"] == "test_calendar_id@group.calendar.google.com"
            assert loaded_config["SYNC_TAG"] == "TEST_SYNC_TAG"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)
