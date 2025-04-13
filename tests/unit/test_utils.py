"""
Unit tests for utility functions.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_environment_variables():
    """Test that environment variables are correctly accessed."""
    # Test with environment variables set
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        assert os.environ.get("TEST_VAR") == "test_value"
        assert os.environ.get("NON_EXISTENT_VAR", "default") == "default"


@pytest.mark.unit
def test_file_operations():
    """Test basic file operations."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write("test content")
        temp_file_path = temp_file.name

    try:
        # Test file exists
        assert os.path.exists(temp_file_path)

        # Test file content
        with open(temp_file_path, "r") as f:
            content = f.read()
        assert content == "test content"
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.mark.unit
def test_mock_google_api():
    """Test mocking of Google API calls."""
    # Create a mock for a Google API service
    mock_service = MagicMock()
    mock_calendar = MagicMock()
    mock_events = MagicMock()

    # Set up the mock chain
    mock_service.calendar.return_value = mock_calendar
    mock_calendar.events.return_value = mock_events
    mock_events.list.return_value.execute.return_value = {
        "items": [
            {"id": "event1", "summary": "Test Event 1"},
            {"id": "event2", "summary": "Test Event 2"},
        ]
    }

    # Test the mock
    result = mock_service.calendar().events().list().execute()
    assert "items" in result
    assert len(result["items"]) == 2
    assert result["items"][0]["id"] == "event1"
    assert result["items"][1]["summary"] == "Test Event 2"
