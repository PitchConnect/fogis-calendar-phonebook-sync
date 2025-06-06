"""Integration tests for the FogisCalendarPhoneBookSync application."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import app
import fogis_calendar_sync
import fogis_contacts
import notification
import token_manager


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

    # Create a mock build function that returns the appropriate service
    # pylint: disable=unused-argument
    def mock_build(service_name, version, credentials=None):
        if service_name == "calendar":
            return mock_calendar_service
        if service_name == "people":
            return mock_people_service
        return MagicMock()

    # Mock subprocess.run to prevent actual command execution
    mock_process = MagicMock()
    mock_process.stdout = "Mock output"
    mock_process.stderr = ""
    mock_process.returncode = 0

    # Patch the necessary functions
    with patch("googleapiclient.discovery.build", side_effect=mock_build), patch(
        "os.path.exists", return_value=True
    ), patch(
        "builtins.open",
        # pylint: disable=consider-using-with, unspecified-encoding
        side_effect=lambda f, *args, **kwargs: (
            open(f, *args, **kwargs) if os.path.exists(f) else MagicMock()
        ),
    ), patch(
        "app.get_version", return_value="test-version"
    ), patch(
        "subprocess.run", return_value=mock_process
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


@pytest.mark.integration
def test_full_authentication_flow():
    """Test the complete authentication flow integration."""
    config = {
        "SCOPES": ["https://www.googleapis.com/auth/calendar"],
        "TOKEN_REFRESH_BUFFER_DAYS": 6,
        "AUTH_SERVER_HOST": "localhost",
        "AUTH_SERVER_PORT": 8080,
    }

    # Test TokenManager integration with proper mocking
    with patch("os.path.exists", return_value=True), patch("builtins.open", create=True), patch(
        "json.load", return_value={"installed": {"client_id": "test"}}
    ):

        tm = token_manager.TokenManager(config)

        # Mock the OAuth flow
        with patch(
            "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file"
        ) as mock_flow_class:
            mock_flow = MagicMock()
            mock_flow.authorization_url.return_value = ("http://auth.url", "state123")
            mock_flow_class.return_value = mock_flow

            # Test initiate auth flow
            auth_url = tm.initiate_auth_flow()
            assert auth_url == "http://auth.url"

            # Test complete auth flow
            mock_creds = MagicMock()
            mock_flow.credentials = mock_creds

            with patch.object(tm, "_save_token", return_value=True):
                result = tm.complete_auth_flow("http://callback.url?code=auth_code")
                assert result is True


@pytest.mark.integration
def test_notification_system_integration():
    """Test the notification system integration."""
    config = {
        "NOTIFICATION_EMAIL_ENABLED": True,
        "NOTIFICATION_EMAIL_SMTP_SERVER": "smtp.gmail.com",
        "NOTIFICATION_EMAIL_SMTP_PORT": 587,
        "NOTIFICATION_EMAIL_FROM": "test@example.com",
        "NOTIFICATION_EMAIL_TO": "recipient@example.com",
        "NOTIFICATION_EMAIL_USERNAME": "test@example.com",
        "NOTIFICATION_EMAIL_PASSWORD": "password",
        "NOTIFICATION_DISCORD_ENABLED": True,
        "NOTIFICATION_DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "NOTIFICATION_SLACK_ENABLED": True,
        "NOTIFICATION_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
    }

    sender = notification.NotificationSender(config)

    # Test email notification via auth notification (which uses _send_email internally)
    with patch.object(sender, "_send_email", return_value=True) as mock_email:
        result = sender.send_auth_notification("http://test.url")
        assert result is True
        mock_email.assert_called_once()

    # Test Discord notification via auth notification
    with patch.object(sender, "_send_discord", return_value=True) as mock_discord:
        # Set method to discord for this test
        sender.method = "discord"
        result = sender.send_auth_notification("http://test.url")
        assert result is True
        mock_discord.assert_called_once()

    # Test Slack notification via auth notification
    with patch.object(sender, "_send_slack", return_value=True) as mock_slack:
        # Set method to slack for this test
        sender.method = "slack"
        result = sender.send_auth_notification("http://test.url")
        assert result is True
        mock_slack.assert_called_once()


@pytest.mark.integration
def test_calendar_and_contacts_sync_integration():
    """Test the integration between calendar and contacts synchronization."""
    # Sample match data with referees
    match_data = {
        "matchid": 12345,
        "lag1namn": "Home Team",
        "lag2namn": "Away Team",
        "anlaggningnamn": "Test Arena",
        "tid": "/Date(1684177200000)/",
        "tavlingnamn": "Test League",
        "domaruppdraglista": [
            {
                "personnamn": "John Referee",
                "mobiltelefon": "+46701234567",
                "epostadress": "john@example.com",
                "domarnr": "REF123",
                "adress": "123 Main St",
                "postnr": "12345",
                "postort": "Stockholm",
                "land": "Sweden",
            }
        ],
        "kontaktpersoner": [],
    }

    # Mock Google services
    mock_calendar_service = MagicMock()
    mock_people_service = MagicMock()

    # Mock calendar operations
    mock_calendar_service.events().list().execute.return_value = {"items": []}
    mock_calendar_service.events().insert().execute.return_value = {
        "id": "event123",
        "summary": "Home Team - Away Team",
    }

    # Mock contacts operations
    mock_people_service.people().connections().list().execute.return_value = {"connections": []}
    mock_people_service.people().connections().list_next.return_value = None
    mock_people_service.contactGroups().list().execute.return_value = {
        "contactGroups": [{"resourceName": "contactGroups/123", "name": "Referees"}]
    }
    mock_people_service.people().createContact().execute.return_value = {
        "resourceName": "people/456"
    }

    # Mock args
    args = MagicMock()
    args.delete = False

    # Test calendar sync
    with patch.dict(
        fogis_calendar_sync.config_dict, {"CALENDAR_ID": "test_calendar", "SYNC_TAG": "TEST"}
    ), patch("fogis_calendar_sync.process_referees", return_value=True):

        fogis_calendar_sync.sync_calendar(match_data, mock_calendar_service, args)

        # Verify calendar event was created
        mock_calendar_service.events().insert.assert_called_once()

    # Test contacts sync
    with patch.object(fogis_contacts, "authorize_google_people", return_value=MagicMock()), patch(
        "googleapiclient.discovery.build", return_value=mock_people_service
    ), patch("time.sleep"):

        result = fogis_contacts.process_referees(match_data)
        assert result is True


@pytest.mark.integration
def test_error_handling_integration():
    """Test error handling across integrated components."""
    from googleapiclient.errors import HttpError

    # Test calendar API error handling
    mock_service = MagicMock()
    mock_service.calendars().get().execute.side_effect = HttpError(
        resp=MagicMock(status=404), content=b'{"error": {"message": "Not found"}}'
    )

    result = fogis_calendar_sync.check_calendar_exists(mock_service, "nonexistent_calendar")
    assert result is False

    # Test contacts API error handling
    mock_service.people().connections().list().execute.side_effect = HttpError(
        resp=MagicMock(status=403), content=b'{"error": {"message": "Forbidden"}}'
    )

    with patch("time.sleep"):
        result = fogis_contacts.test_google_contacts_connection(mock_service)
        assert result is False

    # Test notification error handling
    config = {
        "NOTIFICATION_EMAIL_ENABLED": True,
        "NOTIFICATION_EMAIL_SMTP_SERVER": "invalid.server.com",
        "NOTIFICATION_EMAIL_SMTP_PORT": 587,
        "NOTIFICATION_EMAIL_FROM": "test@example.com",
        "NOTIFICATION_EMAIL_TO": "recipient@example.com",
        "NOTIFICATION_EMAIL_USERNAME": "test@example.com",
        "NOTIFICATION_EMAIL_PASSWORD": "password",
    }

    sender = notification.NotificationSender(config)

    with patch.object(sender, "_send_email", return_value=False):
        result = sender.send_auth_notification("http://test.url")
        assert result is False


@pytest.mark.integration
def test_token_refresh_integration():
    """Test token refresh integration across components."""
    config = {
        "SCOPES": ["https://www.googleapis.com/auth/calendar"],
        "TOKEN_REFRESH_BUFFER_DAYS": 1,
    }

    # Create expired credentials
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token"
    mock_creds.expiry = None

    tm = token_manager.TokenManager(config)

    # Test token expiration check
    with patch.object(tm, "get_credentials", return_value=mock_creds):
        needs_refresh, expiry = tm.check_token_expiration()
        # Since mock_creds.expiry is None, this should handle gracefully
        assert isinstance(needs_refresh, bool)

    # Test getting credentials (which handles refresh internally)
    with patch("os.path.exists", return_value=True), patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=mock_creds
    ):

        # Mock credentials as valid to test the flow
        mock_creds.valid = True
        credentials = tm.get_credentials()
        assert credentials == mock_creds
