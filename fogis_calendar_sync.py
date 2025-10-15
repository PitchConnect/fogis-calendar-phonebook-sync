"""FOGIS Calendar Synchronization Module.

This module synchronizes match data from FOGIS (Swedish Football Association)
with Google Calendar and Contacts.
"""

import argparse
import datetime
import hashlib  # Import for generating hashes
import json
import logging
import os
import sys
from datetime import timedelta, timezone

import google.auth
import google.auth.transport.requests

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from fogis_api_client.enums import MatchStatus
from fogis_api_client.fogis_api_client import FogisApiClient
from fogis_api_client.match_list_filter import MatchListFilter
from google.auth.exceptions import RefreshError  # Correct import for RefreshError
from google.oauth2 import credentials, service_account
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tabulate import tabulate

# Import headless authentication modules
import auth_server
import token_manager
from fogis_contacts import (  # Removed other functions
    process_referees,
    test_google_contacts_connection,
)

# Import enhanced logging
from src.core import configure_logging, get_logger, handle_calendar_errors

# Load environment variables from .env file
load_dotenv()

# Configure enhanced logging
configure_logging(
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    enable_console=os.environ.get("LOG_ENABLE_CONSOLE", "true").lower() == "true",
    enable_file=os.environ.get("LOG_ENABLE_FILE", "true").lower() == "true",
    enable_structured=os.environ.get("LOG_ENABLE_STRUCTURED", "true").lower() == "true",
    log_dir=os.environ.get("LOG_DIR", "logs"),
    log_file=os.environ.get("LOG_FILE", "fogis-calendar-sync.log"),
)

# Get enhanced logger
logger = get_logger(__name__, "calendar_sync")

# Load configuration from config.json
try:
    with open("config.json", "r", encoding="utf-8") as file:
        config_dict = json.load(file)  # Load config data into a dictionary ONCE

    logger.info("Successfully loaded configuration from config.json.")

    # Environment variable override for USE_LOCAL_MATCH_DATA
    # This allows deployment configuration to override the config.json setting
    # without modifying the container image
    env_use_local = os.environ.get("USE_LOCAL_MATCH_DATA")
    if env_use_local is not None:
        # Convert string to boolean (handle "true"/"false" case-insensitively)
        use_local_match_data = env_use_local.lower() in ("true", "1", "yes")
        config_dict["USE_LOCAL_MATCH_DATA"] = use_local_match_data
        logger.info(
            f"USE_LOCAL_MATCH_DATA overridden by environment variable: {use_local_match_data}"
        )
    else:
        logger.info(
            f"USE_LOCAL_MATCH_DATA from config.json: {config_dict.get('USE_LOCAL_MATCH_DATA', False)}"
        )
except FileNotFoundError:
    logger.error("Configuration file not found: config.json. Exiting.")
    sys.exit(1)
except json.JSONDecodeError as err:
    logger.error(f"Error decoding JSON in config.json: {err}. Exiting.")
    sys.exit(1)


def authorize_google_calendar(headless=False):
    """Authorizes access to the Google Calendar API.

    Args:
        headless (bool): Whether to use headless authentication mode

    Returns:
        google.oauth2.credentials.Credentials: The authorized credentials
    """
    if headless:
        logging.info("🔐 OAuth authentication in progress (headless mode)...")
        # Check if token needs refreshing and refresh if needed
        if auth_server.check_and_refresh_auth():
            # Load the refreshed token
            creds = token_manager.load_token()
            if creds and creds.valid:
                logging.info("✅ OAuth authentication established (headless mode)")
                return creds
            else:
                logging.error("❌ Headless OAuth authentication failed")
                return None
        else:
            logging.error("❌ Headless OAuth authentication failed")
            return None

    # Non-headless (interactive) authentication
    creds = None
    logging.info("🔐 OAuth authentication in progress...")

    # Use configurable token path
    token_path = os.environ.get("TOKEN_PATH", "token.json")

    if os.path.exists(token_path):
        try:
            logging.info("📁 Token file found, attempting to load OAuth credentials...")
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                token_path, scopes=config_dict["SCOPES"]
            )
            logging.info(
                "✅ Successfully loaded Google Calendar OAuth credentials from %s",
                token_path,
            )
        except Exception as e:
            logging.error("❌ Error loading OAuth credentials from %s: %s", token_path, e)
            logging.info("🔄 Will attempt to create new OAuth credentials")
            creds = None  # Ensure creds is None if loading fails

    # If there are no (valid) credentials available, let the user log in.
    if not creds:
        logging.info("No credentials found, will create new ones")
    elif not creds.valid:
        logging.info("Credentials found but not valid")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("🔄 OAuth token expired but refresh token available, refreshing...")
            try:
                creds.refresh(google.auth.transport.requests.Request())
                logging.info("✅ Google Calendar OAuth credentials successfully refreshed")
                # Save the refreshed credentials
                token_manager.save_token(creds)
                logging.info("💾 Refreshed OAuth credentials saved to %s", token_path)
            except google.auth.exceptions.RefreshError as e:  # Catch refresh-specific errors
                logging.error(
                    f"❌ Error refreshing Google Calendar OAuth credentials: {e}. Deleting {token_path}."
                )
                token_manager.delete_token()
                logging.info("Deleted invalid token file: %s", token_path)
                creds = None  # Force re-authentication
            except Exception as e:
                logging.error("Error refreshing Google Calendar credentials: %s", e)
                creds = None  # Ensure creds is None if refresh fails

        # Handle the case where creds is None
        if creds is None:
            logging.info("🔄 Attempting to create new OAuth credentials...")
            try:
                logging.info("📁 Using credentials file: %s", config_dict["CREDENTIALS_FILE"])
                # Use token manager for OAuth flow instead of direct flow creation
                # This ensures consistency with the headless authentication approach
                logging.warning("⚠️ Interactive OAuth flow not supported in this context")
                logging.info("💡 Please use manual_auth.py or headless authentication instead")
                return None
            except FileNotFoundError:
                logging.error("❌ Credentials file not found: %s", config_dict["CREDENTIALS_FILE"])
                return None
            except Exception as e:
                logging.error("Error during Google Calendar authorization flow: %s", e)
                return None

    logging.info("Authorization process completed, returning credentials")
    return creds


def generate_match_hash(match):
    """Generates a hash for the relevant parts of the match data, including all referee information."""
    data = {
        "lag1namn": match["lag1namn"],
        "lag2namn": match["lag2namn"],
        "anlaggningnamn": match["anlaggningnamn"],
        "tid": match["tid"],
        "tavlingnamn": match["tavlingnamn"],
        "kontaktpersoner": match.get("kontaktpersoner", []),  # Handle missing key
    }

    # Include all referee information in the hash
    referees = match.get("domaruppdraglista", [])  # Use domaruppdraglista instead of referees
    referee_data = []
    for referee in referees:
        referee_data.append(
            {
                "personnamn": referee.get("personnamn", ""),
                "epostadress": referee.get("epostadress", ""),
                "telefonnummer": referee.get("telefonnummer", ""),
                "adress": referee.get("adress", ""),
            }
        )

    # Sort the referee data to ensure consistent hashing
    referee_data.sort(
        key=lambda x: (
            x["personnamn"],
            x["epostadress"],
            x["telefonnummer"],
            x["adress"],
        )
    )
    data["referees"] = referee_data

    data_string = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data_string).hexdigest()


def generate_calendar_hash(match):
    """Generates a hash for calendar-specific match data (excluding referee information)."""
    data = {
        "lag1namn": match["lag1namn"],
        "lag2namn": match["lag2namn"],
        "anlaggningnamn": match["anlaggningnamn"],
        "tid": match["tid"],
        "tavlingnamn": match["tavlingnamn"],
        "kontaktpersoner": match.get("kontaktpersoner", []),  # Handle missing key
    }

    data_string = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data_string).hexdigest()


def generate_referee_hash(referees):
    """Generates a hash specifically for referee data."""
    if not referees:
        return ""

    referee_data = []
    for referee in referees:
        referee_data.append(
            {
                "personnamn": referee.get("personnamn", ""),
                "epostadress": referee.get("epostadress", ""),
                "telefonnummer": referee.get("telefonnummer", ""),
                "mobiltelefon": referee.get("mobiltelefon", ""),
                "adress": referee.get("adress", ""),
                "postnr": referee.get("postnr", ""),
                "postort": referee.get("postort", ""),
                "land": referee.get("land", ""),
                "domarnr": referee.get("domarnr", ""),
                "domarrollkortnamn": referee.get("domarrollkortnamn", ""),
            }
        )

    # Sort the referee data to ensure consistent hashing
    referee_data.sort(
        key=lambda x: (
            x["personnamn"],
            x["epostadress"],
            x["telefonnummer"],
            x["mobiltelefon"],
            x["adress"],
            x["domarnr"],
        )
    )

    data_string = json.dumps(referee_data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data_string).hexdigest()


class ContactCacheManager:
    """Manages contact-specific cache for independent contact processing."""

    def __init__(self, cache_file_path):
        """Initialize the ContactCacheManager with cache file path."""
        self.cache_file_path = cache_file_path

    def load_contact_cache(self):
        """Load contact cache from file."""
        try:
            with open(self.cache_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.info(
                f"Contact cache file not found: {self.cache_file_path}. Starting with empty cache."
            )
            return {}
        except Exception as e:
            logging.warning(f"Error loading contact cache: {e}")
            return {}

    def save_contact_cache(self, cache_data):
        """Save contact cache to file."""
        try:
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(cache_data, indent=4, ensure_ascii=False))
            logging.debug(f"Contact cache saved with {len(cache_data)} entries")
        except Exception as e:
            logging.error(f"Error saving contact cache: {e}")

    def clear_contact_cache(self):
        """Clear the contact cache file."""
        try:
            if os.path.exists(self.cache_file_path):
                os.remove(self.cache_file_path)
                logging.info(f"Contact cache cleared: {self.cache_file_path}")
        except Exception as e:
            logging.warning(f"Error clearing contact cache: {e}")

    def get_contact_hash(self, match_id):
        """Get the stored contact hash for a match."""
        cache = self.load_contact_cache()
        return cache.get(str(match_id))

    def set_contact_hash(self, match_id, contact_hash):
        """Set the contact hash for a match."""
        cache = self.load_contact_cache()
        cache[str(match_id)] = contact_hash
        self.save_contact_cache(cache)


def process_referees_if_needed(match, contact_cache_manager, force_processing=False):
    """Process referees only if referee data has changed or force_processing is True.

    Args:
        match (dict): Match data containing referee information
        contact_cache_manager (ContactCacheManager): Cache manager for contact hashes
        force_processing (bool): If True, process regardless of cache state

    Returns:
        bool: True if processing was performed or skipped successfully, False if failed
    """
    match_id = str(match["matchid"])
    referees = match.get("domaruppdraglista", [])

    if not referees:
        logging.info(f"Match {match_id}: No referees found, skipping contact processing")
        return True

    # Generate hash for current referee data
    referee_hash = generate_referee_hash(referees)

    # Check if processing is needed
    if not force_processing:
        cached_hash = contact_cache_manager.get_contact_hash(match_id)
        if cached_hash == referee_hash:
            logging.info(f"Match {match_id}: Referee data unchanged, skipping contact processing")
            return True

    logging.info(
        f"Match {match_id}: Processing {len(referees)} referees (force={force_processing})"
    )

    # Process contacts using existing function
    success = process_referees(match)

    if success:
        # Update cache with new hash
        contact_cache_manager.set_contact_hash(match_id, referee_hash)
        logging.info(f"Match {match_id}: Contact processing completed successfully")
    else:
        logging.error(f"Match {match_id}: Contact processing failed")

    return success


def check_calendar_exists(service, calendar_id):
    """Checks if a calendar exists and is accessible."""
    try:
        service.calendars().get(calendarId=calendar_id).execute()
        return True
    except HttpError as error:
        if error.resp.status == 404:
            return False

        logging.error("An error occurred checking calendar existence: %s", error)
        return False
    except Exception as e:
        logging.exception("An unexpected error occurred checking calendar existence: %s", e)
        return None


def find_event_by_match_id(service, calendar_id, match_id):
    """Finds an event in the calendar with the given match ID in extendedProperties."""
    try:
        today = datetime.date.today()
        days_to_look_back = config_dict.get(
            "DAYS_TO_KEEP_PAST_EVENTS", 7
        )  # Default to 7 days if not specified
        from_date = (today - timedelta(days=days_to_look_back)).strftime("%Y-%m-%d")
        time_min_utc = datetime.datetime.combine(
            datetime.datetime.strptime(from_date, "%Y-%m-%d").date(),
            datetime.time.min,
            tzinfo=timezone.utc,
        )
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                privateExtendedProperty=f"matchId={match_id}",
                # Search in extendedProperties
                timeMin=time_min_utc.isoformat(),
                maxResults=1,
                singleEvents=True,  # Optimized for single result
                orderBy="startTime",
            )
            .execute()
        )
    except HttpError as error:
        logging.error("An HTTP error occurred finding event for match %s: %s", match_id, error)
        return None
    except Exception as e:
        logging.exception(
            "An unexpected error occurred while finding event for match %s: %s",
            match_id,
            e,
        )
        return None

    events = events_result.get("items", [])
    if events:
        return events[0]

    return None


def delete_calendar_events(service, match_list):
    """Deletes events from the calendar that correspond to the match list and clears the old_matches dictionary."""
    for match in match_list:
        match_id = str(match["matchid"])
        existing_event = find_event_by_match_id(service, config_dict["CALENDAR_ID"], match_id)
        if existing_event:
            try:
                service.events().delete(
                    calendarId=config_dict["CALENDAR_ID"], eventId=existing_event["id"]
                ).execute()
                print(
                    f"Deleted event: {existing_event['summary']}"
                )  # Removed logging to keep prints clean
            except HttpError as error:
                print(
                    f"An error occurred while deleting event {match_id}: {error}"
                )  # Removed logging to keep prints clean
        else:
            print(
                f"No event found for match ID: {match_id}, skipping deletion."
            )  # Removed logging to keep prints clean


def delete_orphaned_events(service, match_list, days_to_keep_past_events=7):
    """Deletes events from the calendar with SYNC_TAG that are not in the match_list.

    Args:
        service: The Google Calendar service object
        match_list: List of matches from FOGIS
        days_to_keep_past_events: Number of days in the past to look for orphaned events.
            Events older than this will be preserved regardless of match_list.
    """
    existing_match_ids = {
        str(match["matchid"]) for match in match_list
    }  # Use a set for faster lookup

    # Calculate the cutoff date for orphaned events
    today = datetime.date.today()
    from_date = (today - timedelta(days=days_to_keep_past_events)).strftime("%Y-%m-%d")
    time_min_utc = datetime.datetime.combine(
        datetime.datetime.strptime(from_date, "%Y-%m-%d").date(),
        datetime.time.min,
        tzinfo=timezone.utc,
    )

    logging.info(f"Looking for orphaned events from {from_date} onwards")

    try:
        # Retrieve events with the syncTag that are newer than the cutoff date
        events_result = (
            service.events()
            .list(
                calendarId=config_dict["CALENDAR_ID"],
                privateExtendedProperty=f"syncTag={config_dict['SYNC_TAG']}",
                timeMin=time_min_utc.isoformat(),  # Only look at events from cutoff date onwards
                maxResults=2500,  # Max results per page
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except HttpError as error:
        logging.error(f"An error occurred listing calendar events: {error}")
        return

    events = events_result.get("items", [])
    logging.info(f"Found {len(events)} events to check for orphaning")

    orphaned_count = 0
    for event in events:
        match_id = event.get("extendedProperties", {}).get("private", {}).get("matchId")
        event_date = event.get("start", {}).get("dateTime", "Unknown")

        if match_id is None or match_id not in existing_match_ids:
            try:
                service.events().delete(
                    calendarId=config_dict["CALENDAR_ID"], eventId=event["id"]
                ).execute()
                orphaned_count += 1
                logging.info(f"Deleted orphaned event: {event['summary']} on {event_date}")
            except HttpError as error:
                logging.error(f"An error occurred deleting orphaned event: {error}")

    if orphaned_count > 0:
        print(f"Deleted {orphaned_count} orphaned events from {from_date} onwards")
    else:
        print(f"No orphaned events found from {from_date} onwards")


def sync_calendar(match, service, args):
    """Syncs a single match with Google Calendar (contacts handled separately).

    Returns:
        bool: True if calendar sync was performed or skipped successfully, False if failed
    """
    match_id = match["matchid"]
    try:
        # Use calendar-specific hash for change detection
        calendar_hash = generate_calendar_hash(match)

        # Convert Unix timestamp (milliseconds) to datetime object (UTC)
        timestamp = int(match["tid"][6:-2]) / 1000
        start_time_utc = datetime.datetime.fromtimestamp(timestamp, timezone.utc)
        end_time_utc = start_time_utc + datetime.timedelta(hours=2)

        # Build the referees string for description
        referees_details = []
        for referee in match["domaruppdraglista"]:
            details = f"{referee['domarrollkortnamn']}:\n"
            details += f"{referee['personnamn']}\n"
            if referee["mobiltelefon"]:
                details += f"Mobil: {referee['mobiltelefon']}\n"
            if referee["adress"] and referee["postnr"] and referee["postort"]:
                details += f"{referee['adress']}, {referee['postnr']} {referee['postort']}\n"
            referees_details.append(details)
        referees_string = "\n".join(referees_details)

        # Build the contact persons string for description
        contact_details = []
        if "kontaktpersoner" in match and match["kontaktpersoner"]:
            for contact in match["kontaktpersoner"]:
                contact_string = f"{contact['lagnamn']}:\n"
                contact_string += f"Name: {contact['personnamn']}\n"
                if contact["telefon"]:
                    contact_string += f"Tel: {contact['telefon']}\n"
                if contact["mobiltelefon"]:
                    contact_string += f"Mobil: {contact['mobiltelefon']}\n"
                if contact["epostadress"]:
                    contact_string += f"Email: {contact['epostadress']}\n"
                contact_details.append(contact_string)
        contact_string_for_description = "\n".join(
            contact_details
        )  # Renamed to avoid variable shadowing

        # Build the description
        description = f"{match['matchnr']}\n"  # Just the number
        description += f"{match['tavlingnamn']}\n\n"  # Just the competition
        description += f"{referees_string}\n\n"
        if contact_string_for_description:  # Use renamed variable
            description += (
                f"Team Contacts:\n{contact_string_for_description}\n"  # Use renamed variable
            )
        description += (
            f"Match Details: https://www.svenskfotboll.se/matchfakta/{match['matchid']}/\n"
        )

        event_body = {
            "summary": f"{match['lag1namn']} - {match['lag2namn']}",  # Use "-" instead of "vs"
            "location": f"{match['anlaggningnamn']}",
            "start": {
                "dateTime": start_time_utc.isoformat(),  # No need to add 'Z' as it's timezone-aware
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time_utc.isoformat(),  # No need to add 'Z' as it's timezone-aware
                "timeZone": "UTC",
            },
            "description": description,
            "extendedProperties": {
                "private": {
                    "matchId": str(match_id),
                    "syncTag": config_dict["SYNC_TAG"],  # Use config_dict['SYNC_TAG']
                    "calendarHash": calendar_hash,  # Store calendar-specific hash
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "popup",
                        "minutes": 48 * 60,
                    },  # 2 days before (popup) - 48 hours
                ],
            },
        }

        # Check if event exists (e.g., by searching for events with the match_id in the extendedProperties)
        existing_event = find_event_by_match_id(service, config_dict["CALENDAR_ID"], match_id)

        try:
            if existing_event:
                # Get the stored calendar hash from the existing event
                existing_calendar_hash = (
                    existing_event.get("extendedProperties", {})
                    .get("private", {})
                    .get("calendarHash")
                )
                # Also check legacy matchHash for backward compatibility
                if not existing_calendar_hash:
                    existing_calendar_hash = (
                        existing_event.get("extendedProperties", {})
                        .get("private", {})
                        .get("matchHash")
                    )

                # Check if calendar data has changed
                force_calendar = (
                    getattr(args, "force_calendar", False)
                    or getattr(args, "force_all", False)
                    or args.fresh_sync
                )
                if existing_calendar_hash == calendar_hash and not force_calendar:
                    logging.info(
                        f"Match {match_id}: No calendar changes detected, skipping update."
                    )
                    return True  # Calendar sync successful (no changes needed)
                else:
                    # Update existing event
                    updated_event = (
                        service.events()
                        .update(
                            calendarId=config_dict["CALENDAR_ID"],
                            eventId=existing_event["id"],  # Use config_dict['CALENDAR_ID']
                            body=event_body,
                        )
                        .execute()
                    )
                    logging.info("Updated event: %s", updated_event["summary"])  # Use logging
                    if (
                        not args.delete or args.fresh_sync
                    ):  # Process contacts unless delete-only mode
                        if not process_referees(
                            match
                        ):  # Call process_referees, pass people_service and config
                            logging.error(
                                "Error during referee processing: --- check logs in fogis_contacts.py --- "
                            )  # Logging error if process_referees fails
                    return True  # Calendar sync successful
            else:
                # Create new event
                event = (
                    service.events()
                    .insert(calendarId=config_dict["CALENDAR_ID"], body=event_body)
                    .execute()
                )  # Use config_dict['CALENDAR_ID']
                logging.info("Created event: %s", event["summary"])  # Use logging
                if not args.delete or args.fresh_sync:  # Process contacts unless delete-only mode
                    if not process_referees(
                        match
                    ):  # Call process_referees, pass people_service and config
                        logging.error(
                            "Error during referee processing: --- check logs in fogis_contacts.py --- "
                        )  # Logging error if process_referees fails
                return True  # Calendar sync successful

        except HttpError as error:
            logging.error(
                "An error occurred during calendar sync for match %s: %s",
                match_id,
                error,
            )
            return False  # Calendar sync failed

    except Exception as e:
        logging.exception("An unexpected error occurred syncing match %s: %s", match_id, e)
        return False  # Calendar sync failed


@handle_calendar_errors("main_calendar_sync", "main")
def main():
    """Main function to run the FOGIS calendar sync."""
    logger.info("Starting FOGIS calendar sync process")
    parser = argparse.ArgumentParser(description="Syncs FOGIS match data with Google Calendar.")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete existing calendar events before syncing.",
    )
    parser.add_argument(
        "--fresh-sync",
        action="store_true",
        help="Force complete reprocessing of both calendar events and referee contacts, regardless of cached state.",
    )
    parser.add_argument(
        "--force-calendar",
        action="store_true",
        help="Force reprocessing of calendar events only, ignoring calendar cache.",
    )
    parser.add_argument(
        "--force-contacts",
        action="store_true",
        help="Force reprocessing of referee contacts only, ignoring contact cache.",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Force reprocessing of both calendar events and contacts, ignoring all caches.",
    )
    parser.add_argument(
        "--download", action="store_true", help="Downloads data from FOGIS to local."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Use headless authentication mode for server environments.",
    )
    parser.add_argument("--username", dest="fogis_username", required=False, help="FOGIS username")
    parser.add_argument("--password", dest="fogis_password", required=False, help="FOGIS password")
    args = parser.parse_args()

    # Get username and password from arguments or environment variables
    fogis_username = args.fogis_username or os.environ.get("FOGIS_USERNAME")
    fogis_password = args.fogis_password or os.environ.get("FOGIS_PASSWORD")

    fogis_api_client = FogisApiClient(fogis_username, fogis_password)

    if not fogis_username or not fogis_password:
        logger.error("FOGIS_USERNAME and FOGIS_PASSWORD environment variables must be set.")
        return

    cookies = fogis_api_client.login()

    if not cookies:
        logger.error("Login failed.")
        return  # Early exit

    logger.info("Fetching matches, filtering out cancelled games.")
    match_list = (
        MatchListFilter()
        .exclude_statuses([MatchStatus.CANCELLED])
        .fetch_filtered_matches(fogis_api_client)
    )

    if not match_list:
        logging.warning("Failed to fetch match list.")
        return  # Early exit

    print("\n--- Match List ---")
    headers = ["Match ID", "Competition", "Teams", "Date", "Time", "Venue"]
    table_data = [
        [
            match["matchid"],
            (
                match["tavlingnamn"][:40] + "..."
                if len(match["tavlingnamn"]) > 40
                else match["tavlingnamn"]
            ),
            f"{match['lag1namn']} vs {match['lag2namn']}",
            datetime.datetime.fromtimestamp(int(match["tid"][6:-2]) / 1000, timezone.utc).strftime(
                "%Y-%m-%d"
            ),
            datetime.datetime.fromtimestamp(int(match["tid"][6:-2]) / 1000, timezone.utc).strftime(
                "%H:%M"
            ),
            match["anlaggningnamn"],
        ]
        for match in match_list
    ]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Authorize Google Calendar
    creds = authorize_google_calendar(headless=args.headless)

    if not creds:
        logging.error("Failed to obtain Google Calendar Credentials")
        return  # Early exit

    try:
        # Build the service
        service = build("calendar", "v3", credentials=creds)
        people_service = build("people", "v1", credentials=creds)  # Build people_service in main()

        # Check if the calendar is reachable
        if not check_calendar_exists(service, config_dict["CALENDAR_ID"]):
            logging.critical(
                f"Calendar with ID '{config_dict['CALENDAR_ID']}' not found or not accessible. "
                f"Please verify the ID and permissions. Exiting."
            )
            return  # Early exit

        if not test_google_contacts_connection(people_service):
            logging.critical(
                "Google People API is not set up correctly or wrong credentials for People API. Exiting."
            )
            return  # Exit if People API doesn't work

        # Initialize dual cache system
        calendar_cache_file = config_dict["MATCH_FILE"]  # Keep existing file for calendar cache
        contact_cache_file = calendar_cache_file.replace(".json", "_contacts.json")

        contact_cache_manager = ContactCacheManager(contact_cache_file)

        # Handle cache clearing based on command-line arguments
        if args.fresh_sync or args.force_all:
            logging.info("🔄 Fresh sync/force-all requested - clearing all cached data")
            old_matches = {}
            contact_cache_manager.clear_contact_cache()
            # Clear calendar cache file
            try:
                if os.path.exists(calendar_cache_file):
                    os.remove(calendar_cache_file)
                    logging.info("📁 Cleared calendar cache file")
            except Exception as e:
                logging.warning("Failed to clear calendar cache file: %s", e)
        elif args.force_calendar:
            logging.info("🗓️ Force calendar sync requested - clearing calendar cache only")
            old_matches = {}
            try:
                if os.path.exists(calendar_cache_file):
                    os.remove(calendar_cache_file)
                    logging.info("📁 Cleared calendar cache file")
            except Exception as e:
                logging.warning("Failed to clear calendar cache file: %s", e)
        elif args.force_contacts:
            logging.info("👥 Force contact sync requested - clearing contact cache only")
            contact_cache_manager.clear_contact_cache()
            # Load existing calendar cache
            try:
                with open(calendar_cache_file, "r", encoding="utf-8") as f:
                    old_matches = json.load(f)
            except FileNotFoundError:
                logging.warning(
                    "Calendar cache file not found: %s. Starting with empty cache.",
                    calendar_cache_file,
                )
                old_matches = {}
            except Exception as e:
                logging.warning("Error loading calendar cache: %s", e)
                old_matches = {}
        else:
            # Normal operation - load existing caches
            try:
                with open(calendar_cache_file, "r", encoding="utf-8") as f:
                    old_matches = json.load(f)
            except FileNotFoundError:
                logging.warning(
                    "Calendar cache file not found: %s. Starting with empty cache.",
                    calendar_cache_file,
                )
                old_matches = {}
            except Exception as e:
                logging.warning("Error loading calendar cache: %s", e)
                old_matches = {}

        # Delete orphaned events (events with syncTag that are not in the match_list)
        print("\n--- Deleting Orphaned Calendar Events ---")
        days_to_keep = config_dict.get(
            "DAYS_TO_KEEP_PAST_EVENTS", 7
        )  # Default to 7 days if not specified
        logging.info(f"Using {days_to_keep} days as the window for orphaned events detection")
        delete_orphaned_events(service, match_list, days_to_keep)

        if args.delete:
            print(
                "\n--- Deleting Existing Calendar Events ---"
            )  # Removed logging to keep prints clean
            delete_calendar_events(service, match_list)

        # Process each match with independent pipelines
        calendar_processed = 0
        contact_processed = 0
        calendar_skipped = 0
        contact_skipped = 0

        for match in match_list:
            match_id = str(match["matchid"])
            calendar_hash = generate_calendar_hash(match)

            # 1. Handle calendar sync independently
            force_calendar_sync = args.fresh_sync or args.force_calendar or args.force_all
            calendar_needs_sync = (
                force_calendar_sync
                or match_id not in old_matches
                or old_matches[match_id] != calendar_hash
            )

            calendar_updated = False
            if calendar_needs_sync:
                logging.info(f"Match {match_id}: Processing calendar sync")
                calendar_updated = sync_calendar(match, service, args)
                if calendar_updated:
                    calendar_processed += 1
                    # Update calendar cache
                    old_matches[match_id] = calendar_hash
                else:
                    logging.error(f"Match {match_id}: Calendar sync failed")
            else:
                logging.info(f"Match {match_id}: Calendar data unchanged, skipping sync")
                calendar_skipped += 1

            # 2. Handle contact processing independently
            force_contact_sync = args.fresh_sync or args.force_contacts or args.force_all
            contact_updated = process_referees_if_needed(
                match, contact_cache_manager, force_processing=force_contact_sync
            )

            if contact_updated:
                # Check if processing was actually performed (not just skipped)
                referees = match.get("domaruppdraglista", [])
                if referees:
                    referee_hash = generate_referee_hash(referees)
                    cached_hash = contact_cache_manager.get_contact_hash(match_id)
                    if cached_hash == referee_hash and not force_contact_sync:
                        contact_skipped += 1
                    else:
                        contact_processed += 1
                else:
                    contact_skipped += 1

        # Save calendar cache
        logging.info(f"Storing calendar hashes for {len(old_matches)} matches")
        with open(calendar_cache_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(old_matches, indent=4, ensure_ascii=False))

        # Print processing summary
        print("\n--- Processing Summary ---")
        print(f"Calendar events: {calendar_processed} processed, {calendar_skipped} skipped")
        print(f"Contact processing: {contact_processed} processed, {contact_skipped} skipped")

    except HttpError as error:
        logging.error("An HTTP error occurred: %s", error)
    except Exception as e:
        logging.exception("An unexpected error occurred during main process: %s", e)


if __name__ == "__main__":
    main()
