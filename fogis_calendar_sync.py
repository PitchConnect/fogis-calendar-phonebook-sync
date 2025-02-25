import urllib

import requests
import os
import json
import datetime
from datetime import timedelta, timezone
from fogis_api_client.fogis_api_client import FogisApiClient
from tabulate import tabulate
from googleapiclient.discovery import build
from google.oauth2 import service_account
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests
from googleapiclient.errors import HttpError
import argparse
import hashlib  # Import for generating hashes
import logging
from fogis_contacts import process_referees, test_google_contacts_connection  # Removed other functions

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the desired logging level (e.g., INFO, DEBUG, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Customize the log message format
)

class Config:
    """Configuration parameters for the FOGIS to Google Calendar sync."""
    COOKIE_FILE = "fogis_cookies.json"
    CREDENTIALS_FILE = "credentials.json"
    CALENDAR_ID = "your_calendar_id@group.calendar.google.com"  # Make SURE this value is correct
    SYNC_TAG = "FOGIS_CALENDAR_SYNC"
    FOGIS_LOGIN_URL = "https://fogis.svenskfotboll.se/mdk/Login.aspx?ReturnUrl=%2fmdk%2f"
    FOGIS_MATCH_LIST_URL = "https://fogis.svenskfotboll.se/mdk/MatchWebMetoder.aspx/GetMatcherAttRapportera"
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    MATCH_FILE = "matches.json"
    USE_LOCAL_MATCH_DATA = False
    LOCAL_MATCH_DATA_FILE = "local_matches.json"
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/contacts"
    ]


# Load configuration from config.json
try:
    with open('config.json', 'r') as f:
        config_dict = json.load(f)  # Load config data into a dictionary ONCE
    config = Config()  # Instantiate Config class
    config.__dict__.update(config_dict)  # Update Config object from the loaded dictionary
    logging.info("Successfully loaded configuration from config.json.")
except FileNotFoundError:
    logging.error("Configuration file not found: config.json. Exiting.")
    exit()
except json.JSONDecodeError as e:
    logging.error(f"Error decoding JSON in config.json: {e}. Exiting.")
    exit()


def authorize_google_calendar(config):
    """Authorizes access to the Google Calendar API."""
    creds = None
    if os.path.exists('token.json'):
        try:
            logging.debug(f"Scopes: {config.SCOPES}")
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json',
                                                                                    config.SCOPES)
            logging.info("Successfully loaded Google Calendar credentials from token.json.")
        except Exception as e:
            logging.error(f"Error loading credentials from token.json: {e}")
            creds = None  # Ensure creds is None if loading fails

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
                logging.info("Google Calendar credentials Refreshed")
            except google.auth.exceptions.RefreshError as e:  # Catch refresh-specific errors
                logging.error(f"Error refreshing Google Calendar credentials: {e}. Deleting token.json.")
                os.remove("token.json")
                creds = None  # Force re-authentication
            except Exception as e:
                logging.error(f"Error refreshing Google Calendar credentials: {e}")
                creds = None  # Ensure creds is None if refresh fails

        # Handle the case where creds is None
        if creds == None:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(  # Use Imported Class
                    config.CREDENTIALS_FILE, config.SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logging.info("New Google Calendar credentials obtained.")
            except FileNotFoundError:
                logging.error(f"Credentials file not found: {config.CREDENTIALS_FILE}")
                return None
            except Exception as e:
                logging.error(f"Error during Google Calendar authorization flow: {e}")
                return None

        return creds


def generate_match_hash(match):
    """Generates a hash for the relevant parts of the match data."""
    data_string = json.dumps({
        'lag1namn': match['lag1namn'],
        'lag2namn': match['lag2namn'],
        'anlaggningnamn': match['anlaggningnamn'],
        'tid': match['tid'],
        'tavlingnamn': match['tavlingnamn'],
        'domaruppdraglista': match['domaruppdraglista'],
        'kontaktpersoner': match.get('kontaktpersoner', [])  # Handle missing key
    }, sort_keys=True).encode('utf-8')
    return hashlib.sha256(data_string).hexdigest()


def check_calendar_exists(service, calendar_id):
    """Checks if a calendar exists and is accessible."""
    try:
        service.calendars().get(calendarId=calendar_id).execute()
        return True
    except HttpError as error:
        if error.resp.status == 404:
            return False
        else:
            logging.error(f"An error occurred checking calendar existence: {error}")
            return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred checking calendar existence:")
        return None


def find_event_by_match_id(service, calendar_id, match_id, config):
    """Finds an event in the calendar with the given match ID in extendedProperties."""
    try:
        now_utc = datetime.datetime.now(timezone.utc)
        events_result = service.events().list(calendarId=calendar_id,
                                              privateExtendedProperty=f"matchId={match_id}",
                                              # Search in extendedProperties
                                              timeMin=now_utc.isoformat(),
                                              maxResults=1, singleEvents=True,  # Optimized for single result
                                              orderBy='startTime').execute()
    except HttpError as error:
        logging.error(f"An HTTP error occurred finding event for match {match_id}: {error}")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred while finding event for match {match_id}:")
        return None

    events = events_result.get('items', [])
    if events:
        return events[0]
    else:
        return None


def delete_calendar_events(service, match_list, config, old_matches):
    """Deletes events from the calendar that correspond to the match list and clears the old_matches dictionary."""
    for match in match_list:
        match_id = str(match['matchid'])
        existing_event = find_event_by_match_id(service, config.CALENDAR_ID, match_id, config)
        if existing_event:
            try:
                service.events().delete(calendarId=config.CALENDAR_ID, eventId=existing_event['id']).execute()
                print(f"Deleted event: {existing_event['summary']}")  # Removed logging to keep prints clean
            except HttpError as error:
                print(
                    f"An error occurred while deleting event {match_id}: {error}")  # Removed logging to keep prints clean
        else:
            print(
                f"No event found for match ID: {match_id}, skipping deletion.")  # Removed logging to keep prints clean


def delete_orphaned_events(service, match_list, config):
    """Deletes events from the calendar with SYNC_TAG that are not in the match_list."""

    existing_match_ids = {str(match['matchid']) for match in match_list}  # Use a set for faster lookup

    try:
        # Retrieve all events with the syncTag
        events_result = service.events().list(calendarId=config.CALENDAR_ID,
                                              privateExtendedProperty=f"syncTag={config.SYNC_TAG}",
                                              maxResults=2500,  # Max results per page
                                              singleEvents=True,
                                              orderBy='startTime').execute()
    except HttpError as error:
        print(f"An error occurred listing calendar events: {error}")  # Removed logging to keep prints clean
        return

    events = events_result.get('items', [])

    for event in events:
        match_id = event.get('extendedProperties', {}).get('private', {}).get('matchId')

        if match_id is None or match_id not in existing_match_ids:
            try:
                service.events().delete(calendarId=config.CALENDAR_ID, eventId=event['id']).execute()
                print(f"Deleted orphaned event: {event['summary']}")  # Removed logging to keep prints clean
            except HttpError as error:
                print(f"An error occurred deleting orphaned event: {error}")  # Removed logging to keep prints clean


def sync_calendar(match, service, config, args, peopleService):  # Removed People service
    """Syncs a single match with Google Calendar and manages referee contacts."""
    match_id = match['matchid']
    try:
        match_hash = generate_match_hash(match)  # Generate hash for current match data

        # Calendar sync part - unchanged

        if not args.delete:
            if not process_referees(match, config):  # Call process_referees, peopleService NOT passed
                logging.error(
                    "Error during referee processing: --- check logs in fogis_contacts.py --- ")  # Logging error if process_referees fails

    except Exception as e:
        logging.exception(f"An unexpected error occurred syncing match {match_id}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Syncs FOGIS match data with Google Calendar.")
    parser.add_argument("--delete", action="store_true", help="Delete existing calendar events before syncing.")
    parser.add_argument("--download", action="store_true", help="Downloads data from FOGIS to local.")
    args = parser.parse_args()

    fogis_username = os.environ.get('FOGIS_USERNAME')
    fogis_password = os.environ.get('FOGIS_PASSWORD')
    fogis_api_client = FogisApiClient(fogis_username, fogis_password)

    today = datetime.date.today()
    from_date = today.strftime("%Y-%m-%d")  # Today, and one year
    to_date = (today + timedelta(days=365)).strftime("%Y-%m-%d")  # Today, and one year

    if not fogis_username or not fogis_password:
        print("Error: FOGIS_USERNAME and FOGIS_PASSWORD environment variables must be set.")
        return

    session = requests.Session()
    cookies = fogis_api_client.login()

    if not cookies:
        logging.error("Login failed.")
        return  # Early exit

    logging.info(f"Fetching match list from {from_date} to {to_date}")
    match_list = fogis_api_client.fetch_matches_list_json()

    if not match_list:
        logging.warning("Failed to fetch match list.")
        return  # Early exit

    print("\n--- Match List ---")
    headers = ["Match ID", "Competition", "Teams", "Date", "Time", "Venue"]
    table_data = [[
        match['matchid'],
        match['tavlingnamn'][:40] + "..." if len(match['tavlingnamn']) > 40 else match['tavlingnamn'],
        f"{match['lag1namn']} vs {match['lag2namn']}",
        datetime.datetime.fromtimestamp(int(match['tid'][6:-2]) / 1000, timezone.utc).strftime('%Y-%m-%d'),
        datetime.datetime.fromtimestamp(int(match['tid'][6:-2]) / 1000, timezone.utc).strftime('%H:%M'),
        match['anlaggningnamn']
    ] for match in match_list]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Authorize Google Calendar
    creds = authorize_google_calendar(config)

    if not creds:
        logging.error("Failed to obtain Google Calendar Credentials")
        return  # Early exit

    try:
        # Build the service
        service = build('calendar', 'v3', credentials=creds)
        people_service = build('people', 'v1', credentials=creds)  # Build people_service in main()

        # Check if the calendar is reachable
        if not check_calendar_exists(service, config.CALENDAR_ID):
            logging.critical(
                f"Calendar with ID '{config.CALENDAR_ID}' not found or not accessible. Please verify the ID and permissions. Exiting.")
            return  # Early exit

        if not test_google_contacts_connection(people_service, config):
            logging.critical(f"Google People API is not set up correctly or wrong credentials for People API. Exiting.")
            return  # Exit if People API doesn't work

        # Load the old matches from a file
        try:
            old_matches = {}  # Removed file loading for test
        except FileNotFoundError:
            logging.warning(f"Match file not found: {config.MATCH_FILE}. Starting with empty match list.")
            old_matches = {}
        except Exception as e:
            logging.warning(f"An unexpected error occurred while loading old matches: {e}")
            old_matches = {}

        # Delete orphaned events (events with syncTag that are not in the match_list)
        print("\n--- Deleting Orphaned Calendar Events ---")  # Removed logging to keep prints clean
        delete_orphaned_events(service, match_list, config)

        if args.delete:
            print("\n--- Deleting Existing Calendar Events ---")  # Removed logging to keep prints clean
            delete_calendar_events(service, match_list, config, old_matches)

        # Process each match
        for match in match_list:
            match_id = str(match['matchid'])
            match_hash = generate_match_hash(match)

            if match_id in old_matches and old_matches[match_id] == match_hash:
                logging.info(f"Match {match_id}: No changes detected, skipping sync.")
                continue  # Skip to the next match

            sync_calendar(match, service, config, args, people_service)  # Pass people_service to sync_calendar!
            # process_referees(match, people_service, config) # No longer called directly here

            # Store hash
            old_matches[match_id] = match_hash

        logging.info(f"Storing {len(old_matches)} matches")

        with open(config.MATCH_FILE, 'w') as f:
            json.dump(old_matches, f, indent=4, ensure_ascii=False)


    except HttpError as error:
        logging.error(f"An HTTP error occurred: {error}")
    except Exception as e:
        logging.exception(f"An unexpected error occurred during main process: {e}")


if __name__ == "__main__":
    main()
