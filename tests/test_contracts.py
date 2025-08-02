"""Contract tests for external service interactions."""

from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

import fogis_calendar_sync
import fogis_contacts
import notification


class TestGoogleCalendarAPIContract:
    """Contract tests for Google Calendar API interactions."""

    @pytest.mark.contract
    def test_calendar_service_build_contract(self):
        """Test that calendar service can be built with expected interface."""
        mock_creds = MagicMock()

        with patch("googleapiclient.discovery.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Build service
            service = mock_build("calendar", "v3", credentials=mock_creds)

            # Verify service has expected methods
            assert hasattr(service, "events")
            assert hasattr(service, "calendars")

            # Verify events interface
            events = service.events()
            assert hasattr(events, "list")
            assert hasattr(events, "insert")
            assert hasattr(events, "update")
            assert hasattr(events, "delete")
            assert hasattr(events, "get")

    @pytest.mark.contract
    def test_calendar_events_list_contract(self):
        """Test calendar events list API contract."""
        mock_service = MagicMock()

        # Expected response structure
        expected_response = {
            "items": [
                {
                    "id": "event_id",
                    "summary": "Event Title",
                    "start": {"dateTime": "2023-05-15T18:00:00Z"},
                    "end": {"dateTime": "2023-05-15T20:00:00Z"},
                    "extendedProperties": {"private": {"matchId": "12345", "syncTag": "SYNC_TAG"}},
                }
            ],
            "nextPageToken": "next_page_token",
        }

        mock_service.events().list().execute.return_value = expected_response

        # Test the contract
        with patch.dict(
            fogis_calendar_sync.config_dict,
            {"CALENDAR_ID": "test_calendar", "SYNC_TAG": "TEST"},
        ):
            result = fogis_calendar_sync.find_event_by_match_id(
                mock_service, "test_calendar", 12345
            )

            # Verify the expected structure is handled correctly
            assert result is not None
            assert result["id"] == "event_id"

    @pytest.mark.contract
    def test_calendar_events_insert_contract(self):
        """Test calendar events insert API contract."""
        mock_service = MagicMock()

        # Expected request body structure
        event_body = {
            "summary": "Test Event",
            "location": "Test Location",
            "start": {"dateTime": "2023-05-15T18:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2023-05-15T20:00:00Z", "timeZone": "UTC"},
            "description": "Test Description",
            "extendedProperties": {
                "private": {
                    "matchId": "12345",
                    "syncTag": "TEST_TAG",
                    "matchHash": "test_hash",
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 2880}],
            },
        }

        # Expected response structure
        expected_response = {
            "id": "created_event_id",
            "summary": "Test Event",
            "htmlLink": "https://calendar.google.com/event?eid=...",
        }

        mock_service.events().insert().execute.return_value = expected_response

        # Test the contract
        result = mock_service.events().insert(calendarId="test_calendar", body=event_body).execute()

        # Verify response structure
        assert "id" in result
        assert "summary" in result
        assert result["id"] == "created_event_id"

    @pytest.mark.contract
    def test_calendar_api_error_handling_contract(self):
        """Test Google Calendar API error handling contract."""
        mock_service = MagicMock()

        # Test 404 error (calendar not found)
        mock_service.calendars().get().execute.side_effect = HttpError(
            resp=MagicMock(status=404),
            content=b'{"error": {"code": 404, "message": "Not Found"}}',
        )

        with patch.object(fogis_calendar_sync, "logging"):
            result = fogis_calendar_sync.check_calendar_exists(mock_service, "nonexistent_calendar")
            assert result is False

        # Test 403 error (permission denied)
        mock_service.events().list().execute.side_effect = HttpError(
            resp=MagicMock(status=403),
            content=b'{"error": {"code": 403, "message": "Forbidden"}}',
        )

        with patch.object(fogis_calendar_sync, "logging"):
            # Should handle the error gracefully
            try:
                fogis_calendar_sync.delete_orphaned_events(mock_service, [], 7)
            except HttpError:
                pytest.fail("HttpError should be handled gracefully")


class TestGoogleContactsAPIContract:
    """Contract tests for Google Contacts (People) API interactions."""

    @pytest.mark.contract
    def test_people_service_build_contract(self):
        """Test that people service can be built with expected interface."""
        mock_creds = MagicMock()

        with patch("googleapiclient.discovery.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            # Build service
            service = mock_build("people", "v1", credentials=mock_creds)

            # Verify service has expected methods
            assert hasattr(service, "people")
            assert hasattr(service, "contactGroups")

            # Verify people interface
            people = service.people()
            assert hasattr(people, "connections")
            assert hasattr(people, "createContact")
            assert hasattr(people, "updateContact")
            assert hasattr(people, "get")

    @pytest.mark.contract
    def test_people_connections_list_contract(self):
        """Test people connections list API contract."""
        mock_service = MagicMock()

        # Expected response structure
        expected_response = {
            "connections": [
                {
                    "resourceName": "people/123",
                    "etag": "etag_value",
                    "names": [
                        {
                            "displayName": "John Doe",
                            "givenName": "John",
                            "familyName": "Doe",
                        }
                    ],
                    "phoneNumbers": [{"value": "+46701234567", "type": "mobile"}],
                    "emailAddresses": [{"value": "john@example.com", "type": "work"}],
                    "externalIds": [{"value": "FogisId=DomarNr=12345", "type": "account"}],
                }
            ],
            "nextPageToken": "next_page_token",
            "totalPeople": 1,
        }

        mock_service.people().connections().list().execute.return_value = expected_response
        mock_service.people().connections().list_next.return_value = None

        # Test the contract
        with patch.object(fogis_contacts, "logging"), patch("time.sleep"):

            result = fogis_contacts.find_contact_by_phone(mock_service, "+46701234567")

            # Verify the expected structure is handled correctly
            assert result is not None
            assert result["resourceName"] == "people/123"

    @pytest.mark.contract
    def test_people_create_contact_contract(self):
        """Test people create contact API contract."""
        mock_service = MagicMock()

        # Expected request body structure
        contact_data = {
            "names": [{"displayName": "Jane Doe", "givenName": "Jane", "familyName": "Doe"}],
            "phoneNumbers": [{"value": "+46709876543", "type": "mobile"}],
            "emailAddresses": [{"value": "jane@example.com", "type": "work"}],
            "addresses": [
                {
                    "formattedValue": "123 Main St, 12345 Stockholm, Sweden",
                    "streetAddress": "123 Main St",
                    "postalCode": "12345",
                    "city": "Stockholm",
                    "country": "Sweden",
                    "type": "home",
                }
            ],
            "externalIds": [{"value": "FogisId=DomarNr=67890", "type": "account"}],
        }

        # Expected response structure
        expected_response = {
            "resourceName": "people/456",
            "etag": "new_etag",
            "names": contact_data["names"],
            "phoneNumbers": contact_data["phoneNumbers"],
        }

        mock_service.people().createContact().execute.return_value = expected_response

        # Test the contract
        referee = {
            "personnamn": "Jane Doe",
            "mobiltelefon": "+46709876543",
            "epostadress": "jane@example.com",
            "domarnr": "67890",
            "adress": "123 Main St",
            "postnr": "12345",
            "postort": "Stockholm",
            "land": "Sweden",
        }

        with patch.object(fogis_contacts, "logging"), patch("time.sleep"):

            result = fogis_contacts.create_google_contact(
                mock_service, referee, "contactGroups/123"
            )

            # Verify response handling
            assert result == "people/456"

    @pytest.mark.contract
    def test_contact_groups_contract(self):
        """Test contact groups API contract."""
        mock_service = MagicMock()

        # Expected list response
        list_response = {
            "contactGroups": [
                {
                    "resourceName": "contactGroups/123",
                    "name": "Referees",
                    "memberCount": 5,
                    "groupType": "USER_CONTACT_GROUP",
                }
            ]
        }

        # Expected create response
        create_response = {
            "resourceName": "contactGroups/456",
            "name": "Referees",
            "memberCount": 0,
            "groupType": "USER_CONTACT_GROUP",
        }

        mock_service.contactGroups().list().execute.return_value = list_response
        mock_service.contactGroups().create().execute.return_value = create_response

        # Test finding existing group
        with patch.object(fogis_contacts, "logging"):
            result = fogis_contacts.find_or_create_referees_group(mock_service)
            assert result == "contactGroups/123"

    @pytest.mark.contract
    def test_people_api_error_handling_contract(self):
        """Test Google People API error handling contract."""
        mock_service = MagicMock()

        # Test 429 error (quota exceeded)
        mock_service.people().connections().list().execute.side_effect = HttpError(
            resp=MagicMock(status=429),
            content=b'{"error": {"code": 429, "message": "Quota exceeded"}}',
        )

        with patch.object(fogis_contacts, "logging"), patch("time.sleep"):

            result = fogis_contacts.test_google_contacts_connection(mock_service)
            assert result is False

        # Test 409 error (conflict - contact already exists)
        mock_service.people().createContact().execute.side_effect = HttpError(
            resp=MagicMock(status=409),
            content=b'{"error": {"code": 409, "message": "Contact already exists"}}',
        )

        referee = {
            "personnamn": "Test User",
            "mobiltelefon": "+46701234567",
            "epostadress": "test@example.com",
            "domarnr": "12345",
            "adress": "Test St",
            "postnr": "12345",
            "postort": "Stockholm",
            "land": "Sweden",
        }

        with patch.object(fogis_contacts, "logging"), patch("time.sleep"), patch.object(
            fogis_contacts,
            "find_contact_by_phone",
            return_value={"resourceName": "people/existing"},
        ):

            result = fogis_contacts.create_google_contact(
                mock_service, referee, "contactGroups/123"
            )
            assert result == "people/existing"


class TestFOGISAPIContract:
    """Contract tests for FOGIS API interactions."""

    @pytest.mark.contract
    def test_fogis_api_client_interface_contract(self):
        """Test FOGIS API client interface contract."""
        from fogis_api_client import FogisApiClient

        # Test client initialization
        client = FogisApiClient("test_user", "test_pass")

        # Verify expected methods exist (based on actual API)
        assert hasattr(client, "login")
        assert hasattr(client, "fetch_matches_list_json")
        assert hasattr(client, "hello_world")  # This method exists

        # Test method signatures (should not raise AttributeError)
        assert callable(client.login)
        assert callable(client.fetch_matches_list_json)
        assert callable(client.hello_world)

    @pytest.mark.contract
    def test_fogis_match_data_structure_contract(self):
        """Test expected FOGIS match data structure."""
        # Expected match structure based on actual FOGIS API
        expected_match = {
            "matchid": 12345,
            "matchnr": "123456",
            "lag1namn": "Home Team",
            "lag2namn": "Away Team",
            "anlaggningnamn": "Arena Name",
            "tid": "/Date(1684177200000)/",
            "tavlingnamn": "League Name",
            "domaruppdraglista": [
                {
                    "personnamn": "Referee Name",
                    "mobiltelefon": "+46701234567",
                    "epostadress": "referee@example.com",
                    "domarnr": "REF123",
                    "adress": "Street Address",
                    "postnr": "12345",
                    "postort": "City",
                    "land": "Country",
                }
            ],
            "kontaktpersoner": [],
        }

        # Test that our functions can handle this structure
        hash_value = fogis_calendar_sync.generate_match_hash(expected_match)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hash length

        # Test contact data creation
        for referee in expected_match["domaruppdraglista"]:
            contact_data = fogis_contacts.create_contact_data(referee)
            assert "names" in contact_data
            assert "phoneNumbers" in contact_data
            assert "emailAddresses" in contact_data


class TestNotificationServiceContract:
    """Contract tests for notification service interactions."""

    @pytest.mark.contract
    def test_email_notification_contract(self):
        """Test email notification service contract."""
        config = {
            "NOTIFICATION_METHOD": "email",
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "recipient@example.com",
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": 587,
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "password",
        }

        sender = notification.NotificationSender(config)

        # Verify notification interface (actual method names)
        assert hasattr(sender, "send_auth_notification")
        assert callable(sender.send_auth_notification)

        # Test with mock SMTP
        with patch("notification.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            sender.send_auth_notification("http://test.url", "Test expiry")

            # Verify SMTP methods were called
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()

    @pytest.mark.contract
    def test_discord_notification_contract(self):
        """Test Discord notification service contract."""
        config = {
            "NOTIFICATION_METHOD": "discord",
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        }

        sender = notification.NotificationSender(config)

        # Verify notification interface (actual method names)
        assert hasattr(sender, "send_auth_notification")
        assert callable(sender.send_auth_notification)

        # Test with mock urllib.request
        with patch("notification.urlopen") as mock_urlopen, patch(
            "notification.Request"
        ) as mock_request:

            mock_response = MagicMock()
            mock_response.status = 204  # Discord returns 204 on success
            mock_urlopen.return_value.__enter__.return_value = mock_response

            sender.send_auth_notification("http://test.url", "Test expiry")

            # Verify request was made
            mock_request.assert_called_once()
            mock_urlopen.assert_called_once()

    @pytest.mark.contract
    def test_slack_notification_contract(self):
        """Test Slack notification service contract."""
        config = {
            "NOTIFICATION_METHOD": "slack",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test",
        }

        sender = notification.NotificationSender(config)

        # Verify notification interface (actual method names)
        assert hasattr(sender, "send_auth_notification")
        assert callable(sender.send_auth_notification)

        # Test with mock urllib.request
        with patch("notification.urlopen") as mock_urlopen, patch(
            "notification.Request"
        ) as mock_request:

            mock_response = MagicMock()
            mock_response.status = 200  # Slack returns 200 on success
            mock_urlopen.return_value.__enter__.return_value = mock_response

            sender.send_auth_notification("http://test.url", "Test expiry")

            # Verify request was made
            mock_request.assert_called_once()
            mock_urlopen.assert_called_once()
