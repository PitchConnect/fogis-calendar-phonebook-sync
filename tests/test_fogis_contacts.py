"""Tests for the fogis_contacts module."""

from unittest.mock import MagicMock, patch

import pytest

import fogis_contacts


@pytest.fixture
def mock_people_service():
    """Return a mock Google People API service."""
    mock_service = MagicMock()
    mock_service.people().connections().list().execute.return_value = {
        "connections": [
            {
                "resourceName": "people/123",
                "names": [{"displayName": "John Doe"}],
                "phoneNumbers": [{"value": "+46701234567"}]
            }
        ]
    }
    return mock_service


@pytest.fixture
def mock_contact_group():
    """Return a mock contact group."""
    return {
        "resourceName": "contactGroups/123",
        "name": "Referees",
        "memberCount": 1,
        "groupType": "USER_CONTACT_GROUP"
    }


@pytest.mark.unit
def test_find_or_create_group(mock_people_service, mock_contact_group):
    """Test finding or creating a contact group."""
    # Mock the contactGroups().list().execute() chain
    mock_people_service.contactGroups().list().execute.return_value = {
        "contactGroups": [mock_contact_group]
    }
    
    # Call the function under test
    with patch.object(fogis_contacts, "logging"):
        result = fogis_contacts.find_or_create_group(mock_people_service, "Referees")
        
        # Verify the correct group was found
        assert result == "contactGroups/123"
        
        # Test creating a new group
        mock_people_service.contactGroups().list().execute.return_value = {
            "contactGroups": []
        }
        mock_people_service.contactGroups().create().execute.return_value = {
            "resourceName": "contactGroups/456",
            "name": "Referees"
        }
        
        result = fogis_contacts.find_or_create_group(mock_people_service, "Referees")
        assert result == "contactGroups/456"


@pytest.mark.unit
def test_find_contact_by_phone(mock_people_service):
    """Test finding a contact by phone number."""
    # Call the function under test
    with patch.object(fogis_contacts, "logging"):
        result = fogis_contacts.find_contact_by_phone(mock_people_service, "+46701234567")
        
        # Verify the correct contact was found
        assert result["resourceName"] == "people/123"
        
        # Test with a phone number that doesn't exist
        result = fogis_contacts.find_contact_by_phone(mock_people_service, "+46709999999")
        assert result is None


@pytest.mark.unit
def test_create_contact(mock_people_service):
    """Test creating a contact."""
    # Mock the people().createContact().execute() chain
    mock_people_service.people().createContact().execute.return_value = {
        "resourceName": "people/456",
        "names": [{"displayName": "Jane Doe"}],
        "phoneNumbers": [{"value": "+46709876543"}]
    }
    
    # Call the function under test
    with patch.object(fogis_contacts, "logging"):
        result = fogis_contacts.create_contact(
            mock_people_service,
            "Jane Doe",
            "+46709876543",
            "jane.doe@example.com",
            "12345"
        )
        
        # Verify the contact was created correctly
        assert result == "people/456"
        
        # Verify the createContact method was called with the correct parameters
        create_contact_call = mock_people_service.people().createContact.call_args[1]
        contact_to_create = create_contact_call["body"]
        assert contact_to_create["names"][0]["displayName"] == "Jane Doe"
        assert contact_to_create["phoneNumbers"][0]["value"] == "+46709876543"
        assert contact_to_create["emailAddresses"][0]["value"] == "jane.doe@example.com"
        assert contact_to_create["externalIds"][0]["value"] == "12345"
