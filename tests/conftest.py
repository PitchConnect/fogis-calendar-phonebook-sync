"""Pytest configuration file.

This file contains fixtures and configuration for pytest.
"""

import os
import sys

import pytest

# Add the parent directory to sys.path to allow importing modules from the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
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
def sample_match_data():
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
