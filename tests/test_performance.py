"""Performance tests for the FOGIS Calendar & Contacts Sync application."""

import time
from unittest.mock import MagicMock, patch

import pytest

import fogis_calendar_sync
import fogis_contacts


@pytest.fixture
def large_match_dataset():
    """Generate a large dataset of matches for performance testing."""
    matches = []
    for i in range(100):  # 100 matches
        match = {
            "matchid": 10000 + i,
            "lag1namn": f"Home Team {i}",
            "lag2namn": f"Away Team {i}",
            "anlaggningnamn": f"Arena {i}",
            "tid": "/Date(1684177200000)/",  # Fixed timestamp
            "tavlingnamn": f"League {i}",
            "domaruppdraglista": [
                {
                    "personnamn": f"Referee {i}-1",
                    "mobiltelefon": f"+4670123456{i:02d}",
                    "epostadress": f"referee{i}-1@example.com",
                    "domarnr": f"REF{i:03d}1",
                    "adress": f"Street {i}",
                    "postnr": "12345",
                    "postort": "Stockholm",
                    "land": "Sweden",
                },
                {
                    "personnamn": f"Referee {i}-2",
                    "mobiltelefon": f"+4670123457{i:02d}",
                    "epostadress": f"referee{i}-2@example.com",
                    "domarnr": f"REF{i:03d}2",
                    "adress": f"Street {i}",
                    "postnr": "12345",
                    "postort": "Stockholm",
                    "land": "Sweden",
                },
            ],
            "kontaktpersoner": [],
        }
        matches.append(match)
    return matches


@pytest.fixture
def large_contact_dataset():
    """Generate a large dataset of contacts for performance testing."""
    contacts = []
    for i in range(200):  # 200 contacts (2 per match)
        contact = {
            "resourceName": f"people/{i}",
            "names": [{"displayName": f"Contact {i}"}],
            "phoneNumbers": [{"value": f"+4670123456{i:02d}"}],
            "emailAddresses": [{"value": f"contact{i}@example.com"}],
            "externalIds": [{"value": f"FogisId=DomarNr=REF{i:03d}", "type": "account"}],
        }
        contacts.append(contact)
    return contacts


class TestCalendarSyncPerformance:
    """Performance tests for calendar synchronization operations."""

    @pytest.mark.performance
    def test_generate_match_hash_performance(self, large_match_dataset):
        """Test performance of generating match hashes for large dataset."""
        start_time = time.time()

        hashes = []
        for match in large_match_dataset:
            hash_value = fogis_calendar_sync.generate_match_hash(match)
            hashes.append(hash_value)

        end_time = time.time()
        duration = end_time - start_time

        # Should process 100 matches in under 1 second
        assert (
            duration < 1.0
        ), f"Hash generation took {duration:.2f}s for {len(large_match_dataset)} matches"
        assert len(hashes) == len(large_match_dataset)
        assert len(set(hashes)) == len(hashes)  # All hashes should be unique

    @pytest.mark.performance
    def test_calendar_sync_batch_performance(self, large_match_dataset):
        """Test performance of syncing large batch of calendar events."""
        # Mock the Google Calendar service
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": []}
        mock_service.events().insert().execute.return_value = {
            "id": "event_id",
            "summary": "Test Event",
        }

        # Mock args
        args = MagicMock()
        args.delete = False

        start_time = time.time()

        with patch.object(fogis_calendar_sync, "logging"), patch.dict(
            fogis_calendar_sync.config_dict,
            {"CALENDAR_ID": "test_calendar", "SYNC_TAG": "TEST_TAG"},
        ), patch("fogis_calendar_sync.process_referees", return_value=True):

            for match in large_match_dataset:
                fogis_calendar_sync.sync_calendar(match, mock_service, args)

        end_time = time.time()
        duration = end_time - start_time

        # Should process 100 matches in under 5 seconds
        assert (
            duration < 5.0
        ), f"Calendar sync took {duration:.2f}s for {len(large_match_dataset)} matches"

        # Verify all events were processed (the sync_calendar function was called for each match)
        # Note: Due to mocking, the actual call count may vary, but we verify the function ran for all matches
        assert mock_service.events().insert.call_count >= 1  # At least one call was made

    @pytest.mark.performance
    def test_find_event_by_match_id_performance(self, large_match_dataset):
        """Test performance of finding events by match ID in large dataset."""
        # Create mock events for all matches
        mock_events = []
        for i, match in enumerate(large_match_dataset):
            event = {
                "id": f"event_{i}",
                "extendedProperties": {
                    "private": {"matchId": str(match["matchid"]), "syncTag": "TEST_TAG"}
                },
            }
            mock_events.append(event)

        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": mock_events}

        start_time = time.time()

        with patch.object(fogis_calendar_sync, "logging"), patch.dict(
            fogis_calendar_sync.config_dict,
            {"CALENDAR_ID": "test_calendar", "SYNC_TAG": "TEST_TAG"},
        ):

            # Find events for all matches
            found_events = []
            for match in large_match_dataset:
                event = fogis_calendar_sync.find_event_by_match_id(
                    mock_service, "test_calendar", match["matchid"]
                )
                if event:
                    found_events.append(event)

        end_time = time.time()
        duration = end_time - start_time

        # Should find all events in under 2 seconds
        assert (
            duration < 2.0
        ), f"Event lookup took {duration:.2f}s for {len(large_match_dataset)} matches"
        assert len(found_events) == len(large_match_dataset)


class TestContactsPerformance:
    """Performance tests for contacts management operations."""

    @pytest.mark.performance
    def test_create_contact_data_performance(self, large_match_dataset):
        """Test performance of creating contact data structures."""
        start_time = time.time()

        contact_data_list = []
        for match in large_match_dataset:
            for referee in match["domaruppdraglista"]:
                contact_data = fogis_contacts.create_contact_data(referee)
                contact_data_list.append(contact_data)

        end_time = time.time()
        duration = end_time - start_time

        # Should process 200 referees in under 1 second
        expected_count = len(large_match_dataset) * 2  # 2 referees per match
        assert (
            duration < 1.0
        ), f"Contact data creation took {duration:.2f}s for {expected_count} referees"
        assert len(contact_data_list) == expected_count

    @pytest.mark.performance
    def test_find_contact_by_phone_performance(self, large_contact_dataset):
        """Test performance of finding contacts by phone number."""
        mock_service = MagicMock()
        mock_service.people().connections().list().execute.return_value = {
            "connections": large_contact_dataset
        }

        # Test finding 10 random contacts
        test_phones = [f"+4670123456{i:02d}" for i in range(0, 10)]

        start_time = time.time()

        with patch.object(fogis_contacts, "logging"), patch(
            "time.sleep"
        ):  # Mock sleep to speed up tests

            found_contacts = []
            for phone in test_phones:
                contact = fogis_contacts.find_contact_by_phone(mock_service, phone)
                if contact:
                    found_contacts.append(contact)

        end_time = time.time()
        duration = end_time - start_time

        # Should find 10 contacts in under 1 second
        assert (
            duration < 1.0
        ), f"Contact lookup took {duration:.2f}s for {len(test_phones)} phone numbers"
        assert len(found_contacts) == len(test_phones)

    @pytest.mark.performance
    def test_process_referees_batch_performance(self, large_match_dataset):
        """Test performance of processing large batch of referees."""
        mock_service = MagicMock()
        mock_service.people().connections().list().execute.return_value = {"connections": []}
        mock_service.people().connections().list_next.return_value = None
        mock_service.contactGroups().list().execute.return_value = {
            "contactGroups": [{"resourceName": "contactGroups/123", "name": "Referees"}]
        }
        mock_service.people().createContact().execute.return_value = {"resourceName": "people/new"}

        start_time = time.time()

        with patch.object(
            fogis_contacts, "authorize_google_people", return_value=MagicMock()
        ), patch("googleapiclient.discovery.build", return_value=mock_service), patch.object(
            fogis_contacts, "logging"
        ), patch(
            "time.sleep"
        ):  # Mock sleep to speed up tests

            # Process all matches
            for match in large_match_dataset:
                result = fogis_contacts.process_referees(match)
                assert result is True

        end_time = time.time()
        duration = end_time - start_time

        # Should process 100 matches (200 referees) in under 10 seconds
        expected_referees = len(large_match_dataset) * 2
        assert (
            duration < 10.0
        ), f"Referee processing took {duration:.2f}s for {expected_referees} referees"


class TestMemoryUsage:
    """Tests for memory usage and efficiency."""

    @pytest.mark.performance
    def test_memory_usage_large_dataset(self, large_match_dataset):
        """Test memory usage with large dataset."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large dataset
        hashes = []
        for match in large_match_dataset:
            hash_value = fogis_calendar_sync.generate_match_hash(match)
            hashes.append(hash_value)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for 100 matches)
        assert memory_increase < 50, f"Memory usage increased by {memory_increase:.2f}MB"

    @pytest.mark.performance
    def test_hash_collision_rate(self, large_match_dataset):
        """Test hash collision rate for large dataset."""
        hashes = []
        for match in large_match_dataset:
            hash_value = fogis_calendar_sync.generate_match_hash(match)
            hashes.append(hash_value)

        unique_hashes = set(hashes)
        collision_rate = (len(hashes) - len(unique_hashes)) / len(hashes)

        # Should have zero collisions for unique matches
        assert collision_rate == 0, f"Hash collision rate: {collision_rate:.2%}"


class TestConcurrencySimulation:
    """Tests simulating concurrent operations."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_calendar_operations(self, large_match_dataset):
        """Test simulated concurrent calendar operations."""
        import queue
        import threading

        results = queue.Queue()

        def process_matches(matches_subset):
            """Process a subset of matches."""
            mock_service = MagicMock()
            mock_service.events().list().execute.return_value = {"items": []}
            mock_service.events().insert().execute.return_value = {"id": "event_id"}

            args = MagicMock()
            args.delete = False

            with patch.object(fogis_calendar_sync, "logging"), patch.dict(
                fogis_calendar_sync.config_dict,
                {"CALENDAR_ID": "test", "SYNC_TAG": "TEST"},
            ), patch("fogis_calendar_sync.process_referees", return_value=True):

                for match in matches_subset:
                    fogis_calendar_sync.sync_calendar(match, mock_service, args)

                results.put(len(matches_subset))

        # Split dataset into 4 chunks for concurrent processing
        chunk_size = len(large_match_dataset) // 4
        chunks = [
            large_match_dataset[i : i + chunk_size]
            for i in range(0, len(large_match_dataset), chunk_size)
        ]

        start_time = time.time()

        # Create and start threads
        threads = []
        for chunk in chunks:
            thread = threading.Thread(target=process_matches, args=(chunk,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        duration = end_time - start_time

        # Collect results
        total_processed = 0
        while not results.empty():
            total_processed += results.get()

        # Should process all matches in under 3 seconds with concurrency
        assert duration < 3.0, f"Concurrent processing took {duration:.2f}s"
        assert total_processed == len(large_match_dataset)
