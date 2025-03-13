import os
import json
import datetime
from datetime import timedelta, timezone

from fogis_api_client.enums import MatchStatus
from fogis_api_client.fogis_api_client import FogisApiClient
from fogis_api_client.match_list_filter import MatchListFilter
from tabulate import tabulate
from googleapiclient.discovery import build
from google.oauth2 import service_account, credentials
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests
from googleapiclient.errors import HttpError
import argparse
import hashlib  # Import for generating hashes
import logging
from google.auth.exceptions import RefreshError # Correct import for RefreshError
from fogis_contacts import process_referees, test_google_contacts_connection  # Removed other functions

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the desired logging level (e.g., INFO, DEBUG, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Customize the log message format
)

# Load configuration from config.json
try:
    with open('config.json', 'r') as file:
        config_dict = json.load(file)  # Load config data into a dictionary ONCE


    logging.info("Successfully loaded configuration from config.json.")
except FileNotFoundError:
    logging.error("Configuration file not found: config.json. Exiting.")
    exit()
except json.JSONDecodeError as err:
    logging.error(f"Error decoding JSON in config.json: {err}. Exiting.")
    exit()


def authorize_google_calendar():
    """Authorizes access to the Google Calendar API."""
    creds = None
    if os.path.exists('token.json'):
        try:
            logging.debug(f"Scopes: {config_dict['SCOPES']}")
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json',
                                                                                    scopes=config_dict['SCOPES'])
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
        if creds is None:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(  # Use Imported Class
                    config_dict['CREDENTIALS_FILE'], config_dict['SCOPES'])
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.json', 'w', encoding='utf-8') as token:
                    token.write(creds.to_json())
                logging.info("New Google Calendar credentials obtained.")
            except FileNotFoundError:
                logging.error(f"Credentials file not found: {config_dict['CREDENTIALS_FILE']}")
                return None
            except Exception as e:
                logging.error(f"Error during Google Calendar authorization flow: {e}")
                return None

        return creds

def generate_match_hash(match):
    """Generates a hash for the relevant parts of the match data, including all referee information."""
    data = {
        'lag1namn': match['lag1namn'],
        'lag2namn': match['lag2namn'],
        'anlaggningnamn': match['anlaggningnamn'],
        'tid': match['tid'],
        'tavlingnamn': match['tavlingnamn'],
        'kontaktpersoner': match.get('kontaktpersoner', [])  # Handle missing key
    }

    # Include all referee information in the hash
    referees = match.get('domaruppdraglista', [])  # Use domaruppdraglista instead of referees
    referee_data = []
    for referee in referees:
        referee_data.append({
            'personnamn': referee.get('personnamn', ''),
            'epostadress': referee.get('epostadress', ''),
            'telefonnummer': referee.get('telefonnummer', ''),
            'adress': referee.get('adress', '')
        })

    # Sort the referee data to ensure consistent hashing
    referee_data.sort(key=lambda x: (x['personnamn'], x['epostadress'], x['telefonnummer'], x['adress']))
    data['referees'] = referee_data

    data_string = json.dumps(data, sort_keys=True).encode('utf-8')
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
        logging.exception(f"An unexpected error occurred checking calendar existence: {e}")
        return None


def find_event_by_match_id(service, calendar_id, match_id):
    """Finds an event in the calendar with the given match ID in extendedProperties."""
    try:
        today = datetime.date.today()
        from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        time_min_utc = datetime.datetime.combine(datetime.datetime.strptime(from_date, '%Y-%m-%d').date(), datetime.time.min, tzinfo=timezone.utc)
        events_result = service.events().list(calendarId=calendar_id,
                                              privateExtendedProperty=f"matchId={match_id}",
                                              # Search in extendedProperties
                                              timeMin=time_min_utc.isoformat(),
                                              maxResults=1, singleEvents=True,  # Optimized for single result
                                              orderBy='startTime').execute()
    except HttpError as error:
        logging.error(f"An HTTP error occurred finding event for match {match_id}: {error}")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred while finding event for match {match_id}: {e}")
        return None

    events = events_result.get('items', [])
    if events:
        return events[0]
    else:
        return None

def delete_calendar_events(service, match_list):
    """Deletes events from the calendar that correspond to the match list and clears the old_matches dictionary."""
    for match in match_list:
        match_id = str(match['matchid'])
        existing_event = find_event_by_match_id(service, config_dict['CALENDAR_ID'], match_id)
        if existing_event:
            try:
                service.events().delete(calendarId=config_dict['CALENDAR_ID'], eventId=existing_event['id']).execute()
                print(f"Deleted event: {existing_event['summary']}")  # Removed logging to keep prints clean
            except HttpError as error:
                print(
                    f"An error occurred while deleting event {match_id}: {error}")  # Removed logging to keep prints clean
        else:
            print(
                f"No event found for match ID: {match_id}, skipping deletion.")  # Removed logging to keep prints clean


def delete_orphaned_events(service, match_list):
    """Deletes events from the calendar with SYNC_TAG that are not in the match_list."""

    existing_match_ids = {str(match['matchid']) for match in match_list}  # Use a set for faster lookup

    try:
        # Retrieve all events with the syncTag
        events_result = service.events().list(calendarId=config_dict['CALENDAR_ID'],
                                              privateExtendedProperty=f"syncTag={config_dict['SYNC_TAG']}",
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
                service.events().delete(calendarId=config_dict['CALENDAR_ID'], eventId=event['id']).execute()
                print(f"Deleted orphaned event: {event['summary']}")  # Removed logging to keep prints clean
            except HttpError as error:
                print(f"An error occurred deleting orphaned event: {error}")  # Removed logging to keep prints clean


def sync_calendar(match, service, args):
    """Syncs a single match with Google Calendar and manages referee contacts."""
    match_id = match['matchid']
    try:
        match_hash = generate_match_hash(match)  # Generate hash for current match data

        # Convert Unix timestamp (milliseconds) to datetime object (UTC)
        timestamp = int(match['tid'][6:-2]) / 1000
        start_time_utc = datetime.datetime.fromtimestamp(timestamp, timezone.utc)
        end_time_utc = start_time_utc + datetime.timedelta(hours=2)

        # Build the referees string for description
        referees_details = []
        for referee in match['domaruppdraglista']:
            details = f"{referee['domarrollkortnamn']}:\n"
            details += f"{referee['personnamn']}\n"
            if referee['mobiltelefon']:
                details += f"Mobil: {referee['mobiltelefon']}\n"
            if referee['adress'] and referee['postnr'] and referee['postort']:
                details += f"{referee['adress']}, {referee['postnr']} {referee['postort']}\n"
            referees_details.append(details)
        referees_string = "\n".join(referees_details)

        # Build the contact persons string for description
        contact_details = []
        if 'kontaktpersoner' in match and match['kontaktpersoner']:
            for contact in match['kontaktpersoner']:
                contact_string = f"{contact['lagnamn']}:\n"
                contact_string += f"Name: {contact['personnamn']}\n"
                if contact['telefon']:
                    contact_string += f"Tel: {contact['telefon']}\n"
                if contact['mobiltelefon']:
                    contact_string += f"Mobil: {contact['mobiltelefon']}\n"
                if contact['epostadress']:
                    contact_string += f"Email: {contact['epostadress']}\n"
                contact_details.append(contact_string)
        contact_string_for_description = "\n".join(contact_details) # Renamed to avoid variable shadowing

        # Build the description
        description = f"{match['matchnr']}\n"  # Just the number
        description += f"{match['tavlingnamn']}\n\n"  # Just the competition
        description += f"{referees_string}\n\n"
        if contact_string_for_description: # Use renamed variable
            description += f"Team Contacts:\n{contact_string_for_description}\n" # Use renamed variable
        description += f"Match Details: https://www.svenskfotboll.se/matchfakta/{match['matchid']}/\n"

        event_body = {
            'summary': f"{match['lag1namn']} - {match['lag2namn']}",  # Use "-" instead of "vs"
            'location': f"{match['anlaggningnamn']}",
            'start': {
                'dateTime': start_time_utc.isoformat(),  # No need to add 'Z' as it's timezone-aware
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time_utc.isoformat(),  # No need to add 'Z' as it's timezone-aware
                'timeZone': 'UTC',
            },
            'description': description,
            'extendedProperties': {
                'private': {
                    'matchId': str(match_id),
                    'syncTag': config_dict['SYNC_TAG'],  # Use config_dict['SYNC_TAG']
                    'matchHash': match_hash  # Store the hash of the match data
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 48 * 60},  # 2 days before (popup) - 48 hours
                ],
            },
        }

        # Check if event exists (e.g., by searching for events with the match_id in the extendedProperties)
        existing_event = find_event_by_match_id(service, config_dict['CALENDAR_ID'], match_id)

        try:
            if existing_event:
                # Get the stored hash from the existing event
                existing_hash = existing_event.get('extendedProperties', {}).get('private', {}).get('matchHash')

                if existing_hash == match_hash:
                    logging.info(f"Match {match_id}: No changes detected, skipping update.") # Use logging
                else:
                    # Update existing event
                    updated_event = service.events().update(calendarId=config_dict['CALENDAR_ID'], eventId=existing_event['id'], # Use config_dict['CALENDAR_ID']
                                                            body=event_body).execute()
                    logging.info(f"Updated event: {updated_event['summary']}") # Use logging
                    if not args.delete: # Keep contact processing logic - UNCOMMENTED
                        if not process_referees(match):  # Call process_referees, pass people_service and config
                            logging.error(
                                "Error during referee processing: --- check logs in fogis_contacts.py --- ")  # Logging error if process_referees fails
            else:
                # Create new event
                event = service.events().insert(calendarId=config_dict['CALENDAR_ID'], body=event_body).execute() # Use config_dict['CALENDAR_ID']
                logging.info(f"Created event: {event['summary']}") # Use logging
                if not args.delete: # Keep contact processing logic - UNCOMMENTED
                    if not process_referees(match):  # Call process_referees, pass people_service and config
                        logging.error(
                            "Error during referee processing: --- check logs in fogis_contacts.py --- ")  # Logging error if process_referees fails

        except HttpError as error:
            logging.error(f"An error occurred during calendar sync for match {match_id}: {error}") # Use logging

    except Exception as e:
        logging.exception(f"An unexpected error occurred syncing match {match_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Syncs FOGIS match data with Google Calendar.")
    parser.add_argument("--delete", action="store_true", help="Delete existing calendar events before syncing.")
    parser.add_argument("--download", action="store_true", help="Downloads data from FOGIS to local.")
    parser.add_argument('--username', dest='fogis_username', required=False, help='FOGIS username')
    parser.add_argument('--password', dest='fogis_password', required=False, help='FOGIS password')
    args = parser.parse_args()

    # Get username and password from arguments or environment variables
    fogis_username = args.fogis_username or os.environ.get('FOGIS_USERNAME')
    fogis_password = args.fogis_password or os.environ.get('FOGIS_PASSWORD')

    fogis_api_client = FogisApiClient(fogis_username, fogis_password)

    if not fogis_username or not fogis_password:
        print("Error: FOGIS_USERNAME and FOGIS_PASSWORD environment variables must be set.")
        return

    cookies = fogis_api_client.login()

    if not cookies:
        logging.error("Login failed.")
        return  # Early exit

    logging.info("Fetching matches, filtering out cancelled games.")
    match_list = MatchListFilter().exclude_statuses([MatchStatus.CANCELLED]).fetch_filtered_matches(fogis_api_client)

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
    creds = authorize_google_calendar()

    if not creds:
        logging.error("Failed to obtain Google Calendar Credentials")
        return  # Early exit

    try:
        # Build the service
        service = build('calendar', 'v3', credentials=creds)
        people_service = build('people', 'v1', credentials=creds)  # Build people_service in main()

        # Check if the calendar is reachable
        if not check_calendar_exists(service, config_dict['CALENDAR_ID']):
            logging.critical(
                f"Calendar with ID '{config_dict['CALENDAR_ID']}' not found or not accessible. Please verify the ID and permissions. Exiting.")
            return  # Early exit

        if not test_google_contacts_connection(people_service):
            logging.critical(f"Google People API is not set up correctly or wrong credentials for People API. Exiting.")
            return  # Exit if People API doesn't work

        # Load the old matches from a file
        try:
            old_matches = {}  # Removed file loading for test
        except FileNotFoundError:
            logging.warning(f"Match file not found: {config_dict['MATCH_FILE']}. Starting with empty match list.")
            old_matches = {}
        except Exception as e:
            logging.warning(f"An unexpected error occurred while loading old matches: {e}")
            old_matches = {}

        # Delete orphaned events (events with syncTag that are not in the match_list)
        print("\n--- Deleting Orphaned Calendar Events ---")  # Removed logging to keep prints clean
        delete_orphaned_events(service, match_list)

        if args.delete:
            print("\n--- Deleting Existing Calendar Events ---")  # Removed logging to keep prints clean
            delete_calendar_events(service, match_list)

        # Process each match
        for match in match_list:
            match_id = str(match['matchid'])
            match_hash = generate_match_hash(match)

            if match_id in old_matches and old_matches[match_id] == match_hash:
                logging.info(f"Match {match_id}: No changes detected, skipping sync.")
                continue  # Skip to the next match

            sync_calendar(match, service, args)  # Pass from_date to sync_calendar!
            # process_referees(match, people_service, config) # No longer called directly here

            # Store hash
            old_matches[match_id] = match_hash

        logging.info(f"Storing hashes for {len(old_matches)} matches")

        with open(config_dict['MATCH_FILE'], 'w', encoding='utf-8') as f:
            f.write(json.dumps(old_matches, indent=4, ensure_ascii=False))

    except HttpError as error:
        logging.error(f"An HTTP error occurred: {error}")
    except Exception as e:
        logging.exception(f"An unexpected error occurred during main process: {e}")


if __name__ == "__main__":
    main()