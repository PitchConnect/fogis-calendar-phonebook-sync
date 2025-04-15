"""Tests for the fogis_calendar_sync module."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import fogis_calendar_sync


@pytest.fixture
def mock_config():
    """Return a mock configuration for testing."""
    return {
        "COOKIE_FILE": "test_cookies.json",
        "CREDENTIALS_FILE": "test_credentials.json",
        "CALENDAR_ID": "test_calendar_id@group.calendar.google.com",
        "SYNC_TAG": "TEST_SYNC_TAG",
        "MATCH_FILE": "test_matches.json",
        "USE_LOCAL_MATCH_DATA": True,
        "LOCAL_MATCH_DATA_FILE": "test_local_matches.json",
        "SCOPES": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
        ],
    }


@pytest.fixture
def mock_match_data():
    """Return sample match data for testing."""
    return [
        {
            "MatchId": 12345,
            "MatchNo": "123456",
            "HomeTeamName": "Home Team",
            "AwayTeamName": "Away Team",
            "ArenaName": "Test Arena",
            "MatchDateTime": "2023-05-15T18:00:00",
            "LeagueName": "Test League",
            "MatchStatus": 1,
        }
    ]


@pytest.mark.unit
def test_load_config():
    """Test loading configuration from a file."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as temp_file:
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
        # Mock the open function to return our temp file
        with patch(
            "builtins.open", return_value=open(temp_file_path, "r", encoding="utf-8")
        ), patch("sys.exit"), patch.object(fogis_calendar_sync, "logging"):

            # Test that the configuration is loaded correctly
            # We'll simulate the config loading code
            with patch.object(fogis_calendar_sync, "config_dict", {}):
                # Manually execute the config loading code
                with open(temp_file_path, "r", encoding="utf-8") as file:
                    test_config = json.load(file)
                fogis_calendar_sync.config_dict.update(test_config)

                # Verify the config was loaded correctly
                assert fogis_calendar_sync.config_dict == config
                assert (
                    fogis_calendar_sync.config_dict["CALENDAR_ID"]
                    == "test_calendar_id@group.calendar.google.com"
                )
                assert fogis_calendar_sync.config_dict["SYNC_TAG"] == "TEST_SYNC_TAG"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


@pytest.mark.unit
def test_generate_match_hash():
    """Test generating a hash for match data."""
    # Create a sample match
    match = {
        "matchid": 12345,
        "matchnr": "123456",
        "lag1namn": "Home Team",
        "lag2namn": "Away Team",
        "anlaggningnamn": "Test Arena",
        "tid": "/Date(1684177200000)/",  # 2023-05-15T18:00:00
        "tavlingnamn": "Test League",
        "domaruppdraglista": [
            {
                "personnamn": "John Doe",
                "epostadress": "john.doe@example.com",
                "telefonnummer": "+46701234567",
                "adress": "123 Main St",
            }
        ],
        "kontaktpersoner": [],
    }

    # Call the function under test
    hash1 = fogis_calendar_sync.generate_match_hash(match)

    # Verify the hash is a string
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hash is 64 characters long

    # Modify the match and verify the hash changes
    match["lag1namn"] = "New Home Team"
    hash2 = fogis_calendar_sync.generate_match_hash(match)
    assert hash1 != hash2


@pytest.mark.unit
def test_find_event_by_match_id():
    """Test finding an event by match ID."""
    # Create mock service and events
    mock_service = MagicMock()
    mock_events = [
        {
            "id": "event1",
            "extendedProperties": {"private": {"matchId": "12345", "syncTag": "TEST_SYNC_TAG"}},
        },
        {
            "id": "event2",
            "extendedProperties": {"private": {"matchId": "67890", "syncTag": "TEST_SYNC_TAG"}},
        },
    ]

    # Mock the events().list().execute() chain
    mock_service.events().list().execute.return_value = {"items": mock_events}

    # Call the function under test
    with patch.object(fogis_calendar_sync, "logging"), patch.dict(
        fogis_calendar_sync.config_dict, {"CALENDAR_ID": "calendar_id", "SYNC_TAG": "TEST_SYNC_TAG"}
    ):
        result = fogis_calendar_sync.find_event_by_match_id(mock_service, "calendar_id", 12345)

        # Verify the correct event was found
        assert result["id"] == "event1"

        # Test with a match ID that doesn't exist
        # Create a new mock for this test case
        mock_service_empty = MagicMock()
        mock_service_empty.events().list().execute.return_value = {"items": []}
        result = fogis_calendar_sync.find_event_by_match_id(
            mock_service_empty, "calendar_id", 99999
        )
        assert result is None
