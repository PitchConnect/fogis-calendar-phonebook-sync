"""Tests for the token_manager module."""

import datetime
import json
import os
import tempfile
from unittest import mock

import pytest
from google.oauth2.credentials import Credentials

import token_manager


@pytest.fixture
def mock_token_file():
    """Create a temporary token file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "expiry": (datetime.datetime.now() + datetime.timedelta(days=5)).isoformat()
        }
        temp_file.write(json.dumps(token_data).encode())
        temp_file_name = temp_file.name
    
    # Mock the token file path
    original_token_file = token_manager.TOKEN_FILE
    token_manager.TOKEN_FILE = temp_file_name
    
    yield temp_file_name
    
    # Cleanup
    token_manager.TOKEN_FILE = original_token_file
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.fixture
def mock_metadata_file():
    """Create a temporary token metadata file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        metadata = {
            "token_type": "google_oauth",
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": (datetime.datetime.now() + datetime.timedelta(days=5)).isoformat(),
            "scopes": ["https://www.googleapis.com/auth/calendar"]
        }
        temp_file.write(json.dumps(metadata).encode())
        temp_file_name = temp_file.name
    
    # Mock the metadata file path
    original_metadata_file = token_manager.TOKEN_METADATA_FILE
    token_manager.TOKEN_METADATA_FILE = temp_file_name
    
    yield temp_file_name
    
    # Cleanup
    token_manager.TOKEN_METADATA_FILE = original_metadata_file
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.mark.fast
def test_load_token(mock_token_file):
    """Test loading a token from a file."""
    # Mock the config.json file
    with mock.patch("builtins.open", mock.mock_open(read_data='{"SCOPES": ["https://www.googleapis.com/auth/calendar"]}')):
        creds = token_manager.load_token()
    
    assert creds is not None
    assert isinstance(creds, Credentials)
    assert creds.refresh_token == "test_refresh_token"


@pytest.mark.fast
def test_save_token():
    """Test saving a token to a file."""
    # Create a mock credentials object
    creds = mock.MagicMock()
    creds.to_json.return_value = '{"token": "test_token"}'
    creds.expiry = datetime.datetime.now() + datetime.timedelta(days=5)
    creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    
    # Mock the open function for both files
    with mock.patch("builtins.open", mock.mock_open()) as mock_open:
        result = token_manager.save_token(creds)
    
    assert result is True
    assert mock_open.call_count == 2  # Once for token.json, once for metadata


@pytest.mark.fast
def test_is_token_expiring_soon():
    """Test checking if a token is expiring soon."""
    # Create a mock credentials object that is not expiring soon
    creds = mock.MagicMock()
    creds.valid = True
    creds.expiry = datetime.datetime.now() + datetime.timedelta(days=5)
    
    # Token should not be expiring soon with default buffer (1 day)
    assert not token_manager.is_token_expiring_soon(creds)
    
    # Token should be expiring soon with a larger buffer (6 days)
    assert token_manager.is_token_expiring_soon(creds, buffer_days=6)
    
    # Create a mock credentials object that is expiring soon
    creds.expiry = datetime.datetime.now() + datetime.timedelta(hours=12)
    
    # Token should be expiring soon with default buffer (1 day)
    assert token_manager.is_token_expiring_soon(creds)


@pytest.mark.fast
def test_refresh_token():
    """Test refreshing a token."""
    # Create a mock credentials object
    creds = mock.MagicMock()
    creds.refresh_token = "test_refresh_token"
    
    # Mock the refresh method
    with mock.patch.object(creds, "refresh") as mock_refresh:
        with mock.patch.object(token_manager, "save_token", return_value=True) as mock_save:
            new_creds, success = token_manager.refresh_token(creds)
    
    assert success is True
    assert new_creds is creds
    mock_refresh.assert_called_once()
    mock_save.assert_called_once_with(creds)


@pytest.mark.fast
def test_delete_token():
    """Test deleting a token."""
    # Create temporary files to delete
    with tempfile.NamedTemporaryFile(delete=False) as token_file:
        token_file_name = token_file.name
    
    with tempfile.NamedTemporaryFile(delete=False) as metadata_file:
        metadata_file_name = metadata_file.name
    
    # Mock the file paths
    original_token_file = token_manager.TOKEN_FILE
    original_metadata_file = token_manager.TOKEN_METADATA_FILE
    token_manager.TOKEN_FILE = token_file_name
    token_manager.TOKEN_METADATA_FILE = metadata_file_name
    
    try:
        # Test deleting the files
        result = token_manager.delete_token()
        
        assert result is True
        assert not os.path.exists(token_file_name)
        assert not os.path.exists(metadata_file_name)
    finally:
        # Restore original paths
        token_manager.TOKEN_FILE = original_token_file
        token_manager.TOKEN_METADATA_FILE = original_metadata_file
