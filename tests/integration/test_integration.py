"""Integration tests for the FogisCalendarPhoneBookSync application."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import app
import fogis_calendar_sync
import fogis_contacts


@pytest.fixture
def setup_test_environment():
    """Set up the test environment with mock data."""
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock config file
        config = {
            "COOKIE_FILE": os.path.join(temp_dir, "cookies.json"),
            "CREDENTIALS_FILE": os.path.join(temp_dir, "credentials.json"),
            "CALENDAR_ID": "test_calendar_id@group.calendar.google.com",
            "SYNC_TAG": "TEST_SYNC_TAG",
            "MATCH_FILE": os.path.join(temp_dir, "matches.json"),
            "USE_LOCAL_MATCH_DATA": True,
            "LOCAL_MATCH_DATA_FILE": os.path.join(temp_dir, "local_matches.json"),
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
            ],
        }

        with open(os.path.join(temp_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f)

        # Create a mock matches file
        matches = [
            {
                "MatchId": 12345,
                "MatchNo": "123456",
                "HomeTeamName": "Home Team",
                "AwayTeamName": "Away Team",
                "ArenaName": "Test Arena",
                "MatchDateTime": "2023-05-15T18:00:00",
                "LeagueName": "Test League",
                "MatchStatus": 1,
                "Referees": [
                    {
                        "Name": "John Doe",
                        "Phone": "+46701234567",
                        "Email": "john.doe@example.com",
                        "FogisId": "12345",
                    }
                ],
            }
        ]

        with open(os.path.join(temp_dir, "local_matches.json"), "w", encoding="utf-8") as f:
            json.dump(matches, f)

        yield temp_dir, config, matches


@pytest.mark.integration
# pylint: disable=redefined-outer-name
def test_end_to_end_sync(setup_test_environment):
    """Test the end-to-end sync process."""
    temp_dir, _, _ = setup_test_environment  # We only need the temp_dir

    # Mock the Google API services
    mock_calendar_service = MagicMock()
    mock_people_service = MagicMock()

    # Mock the calendar events list
    mock_calendar_service.events().list().execute.return_value = {"items": []}

    # Mock the calendar events insert
    mock_calendar_service.events().insert().execute.return_value = {
        "id": "event1",
        "summary": "Home Team vs Away Team",
        "description": "MatchId: 12345\nTEST_SYNC_TAG",
    }

    # Mock the people service
    mock_people_service.contactGroups().list().execute.return_value = {"contactGroups": []}
    mock_people_service.contactGroups().create().execute.return_value = {
        "resourceName": "contactGroups/123",
        "name": "Referees",
    }
    mock_people_service.people().connections().list().execute.return_value = {"connections": []}
    mock_people_service.people().createContact().execute.return_value = {
        "resourceName": "people/123",
        "names": [{"displayName": "John Doe"}],
        "phoneNumbers": [{"value": "+46701234567"}],
    }

    # Patch the necessary functions
    with patch(
        "googleapiclient.discovery.build",
        side_effect=lambda service, version, credentials: (
            mock_calendar_service if service == "calendar" else mock_people_service
        ),
    ), patch.object(
        fogis_contacts, "authorize_google_people", return_value=MagicMock()
    ), patch.object(
        fogis_calendar_sync, "logging", MagicMock()
    ), patch.object(
        fogis_contacts, "logging", MagicMock()
    ), patch(
        "subprocess.run", return_value=MagicMock(returncode=0, stdout="Success", stderr="")
    ), patch(
        "os.path.exists", return_value=True
    ), patch(
        "builtins.open",
        # pylint: disable=consider-using-with, unspecified-encoding
        side_effect=lambda f, *args, **kwargs: (
            open(f, *args, **kwargs) if os.path.exists(f) else MagicMock()
        ),
    ):

        # Override the config.json path
        with patch.dict(os.environ, {"CONFIG_PATH": os.path.join(temp_dir, "config.json")}):
            # Run the sync process
            with app.app.test_client() as client:
                response = client.post("/sync")

                # Verify the response
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == "success"

                # Verify that the calendar service was called
                mock_calendar_service.events().insert.assert_called_once()

                # Verify that the people service was called
                mock_people_service.contactGroups().create.assert_called_once()
                mock_people_service.people().createContact.assert_called_once()
