"""FOGIS Contacts Management Module.

This module manages contacts from FOGIS (Swedish Football Association)
and synchronizes them with Google Contacts.
"""

import logging
import os
import time  # Import time for sleep

import google.auth

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import credentials, service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables from .env file
load_dotenv()


SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/contacts"]

CREDENTIALS_FILE = "credentials.json"

MAX_RETRIES_GOOGLE_API = 5
BACKOFF_FACTOR_GOOGLE_API = 2
BASE_DELAY_GOOGLE_API = 60  # Increased base delay to 60 seconds for quota errors!
DELAY_BETWEEN_CONTACT_CALLS = 1  # Increased delay between calls to 1 second!


def authorize_google_people():
    """Authorizes access to the Google People API."""
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                "token.json", SCOPES
            )
            logging.info("Successfully loaded Google People credentials from token.json.")
        except Exception as e:
            logging.error("Error loading credentials from token.json: %s", e)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
                # Save the refreshed credentials
                with open("token.json", "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                logging.info("Google People credentials Refreshed and saved")
            except Exception as e:
                logging.error("Error refreshing credentials: %s", e)
                # If refresh fails, try to get new credentials
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open("token.json", "w", encoding="utf-8") as token:
                        token.write(creds.to_json())
                    logging.info("New Google People Creds Auth Completed after refresh failure")
                except Exception as inner_e:
                    logging.error(
                        "Failed to get new credentials after refresh failure: %s", inner_e
                    )
                    return None
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open("token.json", "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                logging.info("New Google People Creds Auth Completed")
            except Exception as e:
                logging.error("Error during authorization flow: %s", e)
                return None
    return creds


def find_or_create_referees_group(service):
    """Finds the 'Referees' group or creates it if it doesn't exist."""
    group_name = "Referees"

    for attempt in range(MAX_RETRIES_GOOGLE_API):  # Retry loop
        try:
            results = service.contactGroups().list(pageSize=10).execute()
            groups = results.get("contactGroups", [])
            logging.info("  - Contact groups fetched")

            for group in groups:
                if group["name"] == group_name:
                    logging.info(
                        f"  - Existing '{group_name}' group found with ID: {group['resourceName']}"
                    )
                    return group["resourceName"]

            logging.info("  - '%s' group not found, creating...", group_name)
            group_body = {"contactGroup": {"name": group_name}}
            create_result = service.contactGroups().create(body=group_body).execute()
            new_group_id = create_result["resourceName"]
            logging.info("  - Created new '%s' group with ID: %s", group_name, new_group_id)
            return new_group_id

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded, retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded, max retries reached. Error: {error}"
                    )
                    print(f"Full error details: {error.content.decode()}")
                    return None  # Return None to indicate failure
            else:  # Other HTTP errors
                logging.error("An HTTP error occurred: %s", error)
                print(f"Full error details: {error.content.decode()}")
                return None
        except Exception as e:
            logging.exception("An unexpected error occurred while finding or creating group: %s", e)
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def process_referees(match):
    """Manages referees contacts."""
    creds = authorize_google_people()
    if not creds:
        logging.error("Failed to obtain Google People API credentials for referee processing.")
        return False

    try:
        service = build("people", "v1", credentials=creds)

        for referee in match["domaruppdraglista"]:
            name = referee["personnamn"]
            phone = referee["mobiltelefon"]
            try:
                existing_contact = find_contact_by_name_and_phone(service, name, phone, referee)

                if existing_contact:
                    update_google_contact(service, existing_contact["resourceName"], referee)
                    logging.info("Updated contact for referee: %s", name)
                else:
                    group_id = find_or_create_referees_group(service)
                    if group_id:
                        create_google_contact(service, referee, group_id)
                        logging.info("Created contact for referee: %s", name)
                    else:
                        logging.error("Could not find group ID, skipping contact creation")

            except Exception as e:
                logging.exception("An error occurred managing contact for referee %s: %s", name, e)
        return True
    except Exception as e:
        logging.exception("An unexpected error occurred building people service: %s", e)
        return False


def find_contact_by_name_and_phone(service, name, phone, referee):
    """Finds a contact in Google Contacts by domarNr, or fallback to phone number."""
    domar_nr = referee.get("domarnr")

    # --- Lookup by externalId (FogisId=DomarNr) with Pagination and Retry ---
    if domar_nr:
        fogis_external_id_value = f"FogisId=DomarNr={domar_nr}"

        for attempt in range(MAX_RETRIES_GOOGLE_API):
            try:
                all_connections = []
                request = (
                    service.people()
                    .connections()
                    .list(
                        resourceName="people/me",
                        personFields="names,phoneNumbers,externalIds",
                        pageSize=1000,
                    )
                )
                while request:
                    results = request.execute()
                    connections = results.get("connections", [])
                    all_connections.extend(connections)
                    request = service.people().connections().list_next(request, results)

                if all_connections:
                    for person in all_connections:
                        if "externalIds" in person:
                            for external_id in person["externalIds"]:
                                if (
                                    external_id.get("type") == "account"
                                    and external_id.get("value") == fogis_external_id_value
                                ):
                                    logging.info(
                                        f"  - Contact found by FogisId=DomarNr: {domar_nr}"
                                    )
                                    return person
                break  # Break retry loop if successful (or not found)

            except HttpError as error:
                if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                    if attempt < MAX_RETRIES_GOOGLE_API - 1:
                        delay = BASE_DELAY_GOOGLE_API * (
                            BACKOFF_FACTOR_GOOGLE_API**attempt
                        )  # Using increased BASE_DELAY
                        logging.warning(
                            f"Google People API Quota exceeded (FogisId lookup), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                        )
                        time.sleep(delay)
                    else:
                        logging.error(
                            f"Google People API Quota exceeded (FogisId lookup), max retries reached. Error: {error}"
                        )
                        print(
                            f"   Full error details (FogisId paginated lookup): {error.content.decode()}"
                        )
                        break
                else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                    logging.error("An HTTP error occurred during FogisId lookup: %s", error)
                    print(
                        f"   Full error details (FogisId paginated lookup): {error.content.decode()}"
                    )
                    break
            except Exception as e:
                logging.exception(
                    f"An unexpected error occurred during FogisId lookup (paginated): {e}"
                )
                return None
            time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay

    # --- Fallback Lookup by Phone Number with Pagination and Retry ---
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            all_connections = []
            request = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me", personFields="names", pageSize=1000  # phoneNumbers',
                )
            )
            while request:
                results = request.execute()
                connections = results.get("connections", [])
                all_connections.extend(connections)
                request = service.people().connections().list_next(request, results)

            if all_connections:
                for person in all_connections:
                    if "phoneNumbers" in person:
                        for phone_number in person["phoneNumbers"]:
                            if phone_number["value"] == phone:
                                logging.info(
                                    f"  - Contact found by phone number (fallback, paginated): {phone}"
                                )
                                return person
                logging.info(
                    f"  - Contact not found for name '{name}' and phone '{phone}' (paginated search)"
                )
                return None  # Not found by either method
            break  # Break retry loop if successful (or not found)

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (phone lookup), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (phone lookup), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (phone paginated lookup): {error.content.decode()}"
                    )
                    return None
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error(
                    f"An HTTP error occurred during phone number lookup (paginated): {error}"
                )
                print(f"   Full error details (phone paginated lookup): {error.content.decode()}")
                return None
        except Exception as e:
            logging.exception(
                f"An unexpected error occurred during phone number lookup (paginated): {e}"
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None


def update_google_contact(service, contact_id, referee):
    """Updates a contact in Google Contacts."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            # Retrieve the existing contact information
            existing_contact = (
                service.people()
                .get(
                    resourceName=contact_id,
                    personFields="names,phoneNumbers,emailAddresses,organizations,addresses",
                )
                .execute()
            )

            existing_etag = existing_contact["etag"]

            updated_names = existing_contact.get("names", [])
            updated_phone_numbers = existing_contact.get("phoneNumbers", [])
            updated_email_addresses = existing_contact.get("emailAddresses", [])
            updated_organizations = existing_contact.get("organizations", [])
            updated_addresses = existing_contact.get("addresses", [])

            if referee["mobiltelefon"]:
                new_phone_number = {"value": referee["mobiltelefon"], "type": "mobile"}
                if (
                    not updated_phone_numbers
                    or updated_phone_numbers[0].get("value") != referee["mobiltelefon"]
                ):
                    updated_phone_numbers = [new_phone_number]

            updated_contact_data = {
                "etag": existing_etag,
                "names": updated_names,
                "phoneNumbers": updated_phone_numbers,
                "emailAddresses": updated_email_addresses,
                "organizations": updated_organizations,
                "addresses": updated_addresses,
            }

            service.people().updateContact(
                resourceName=contact_id,
                body=updated_contact_data,
                updatePersonFields="names,phoneNumbers,emailAddresses,organizations,addresses",
            ).execute()

            logging.info(
                f"  - Updated contact for referee: {referee['personnamn']} with ID: {contact_id}"
            )
            return contact_id  # Return contact id on success

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (contact update), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (contact update), max retries reached. Error: {error}"
                    )
                    print(f"   Full error details (contact update): {error.content.decode()}")
                    return None  # Return None on max retries
            elif (
                error.resp.status == 400
                and 'Invalid personFields mask path: "notes"' in error.content.decode()
            ):
                logging.warning(
                    f"Ignoring error 400 - Invalid personFields path 'notes'. Proceeding without updating notes. Full error: {error}"
                )
                return contact_id  # Return contact id and proceed without notes - specific error handling
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error("An HTTP error occurred updating contact %s: %s", contact_id, error)
                print(f"   Full error details (contact update): {error.content.decode()}")
                return None  # Return None for other errors
        except Exception as e:
            logging.exception("An unexpected error occurred while updating contact: %s", e)
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def create_contact_data(referee, match_date_str=None):
    """Creates a Google Contact data structure from referee information."""
    contact_data = {
        "names": [
            {
                "displayName": referee["personnamn"],
                "givenName": referee["personnamn"].split()[0] if referee["personnamn"] else "",
                "familyName": referee["personnamn"].split()[-1] if referee["personnamn"] else "",
            }
        ],
        "phoneNumbers": [{"value": referee["mobiltelefon"], "type": "mobile"}],
        "emailAddresses": [{"value": referee["epostadress"], "type": "work"}],
        "addresses": [
            {
                "formattedValue": f"{referee['adress']}, {referee['postnr']} {referee['postort']}, {referee['land']}",
                "streetAddress": referee["adress"],
                "postalCode": referee["postnr"],
                "city": referee["postort"],
                "country": referee["land"],
                "type": "home",
            }
        ],
        "externalIds": [{"value": f"FogisId=DomarNr={referee['domarnr']}", "type": "account"}],
    }

    if match_date_str:
        contact_data["importantDates"] = [
            {
                "label": "Refereed Until",
                "dateTime": {
                    "year": int(match_date_str.split("-")[0]),
                    "month": int(match_date_str.split("-")[1]),
                    "day": int(match_date_str.split("-")[2]),
                },
                "type": "other",
            }
        ]

    contact_data["phoneNumbers"] = [
        number for number in contact_data.get("phoneNumbers", []) if number.get("value")
    ]
    contact_data["emailAddresses"] = [
        email for email in contact_data.get("emailAddresses", []) if email.get("value")
    ]
    contact_data["organizations"] = [
        org for org in contact_data.get("organizations", []) if org.get("title")
    ]
    contact_data["addresses"] = [
        addr for addr in contact_data.get("addresses", []) if addr.get("formattedValue")
    ]
    contact_data["externalIds"] = [
        ext_id for ext_id in contact_data.get("externalIds", []) if ext_id.get("value")
    ]

    return contact_data


def find_contact_by_phone(service, phone):
    """Finds a contact in Google Contacts by phone number."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            results = (
                service.people()
                .connections()
                .list(resourceName="people/me", personFields="names,phoneNumbers", pageSize=100)
                .execute()
            )
            connections = results.get("connections", [])

            if connections:
                for person in connections:
                    if "phoneNumbers" in person:
                        for phone_number in person["phoneNumbers"]:
                            if phone_number["value"] == phone:
                                logging.info(
                                    f"  - Existing contact found for phone number: {phone}"
                                )
                                return person
            return (
                None  # Return None if not found in this attempt, will retry or finally return None
            )

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded (find_contact_by_phone), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (find_contact_by_phone), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (find_contact_by_phone): {error.content.decode()}"
                    )
                    return None  # Return None if max retries reached
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error("An HTTP error occurred in find_contact_by_phone(): %s", error)
                print(f"   Full error details (find_contact_by_phone): {error.content.decode()}")
                return None  # Return None for other errors
        except Exception as e:
            logging.exception("An unexpected error occurred in find_contact_by_phone(): %s", e)
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def create_google_contact(service, referee, group_id):
    """Creates a new contact in Google Contacts and adds it to the specified group."""
    contact_data = create_contact_data(referee)

    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            person = service.people().createContact(body=contact_data).execute()
            contact_id = person["resourceName"]
            logging.info(
                f"  - Created contact for referee: {referee['personnamn']} with ID: {contact_id}"
            )

            if group_id:
                try:
                    service.contactGroups().members().modify(
                        resourceName=group_id, body={"resourceNamesToAdd": [contact_id]}
                    ).execute()
                    logging.info(
                        f"  - Added contact '{referee['personnamn']}' to 'Referees' group."
                    )
                except HttpError as e:
                    if e.resp.status == 400:
                        logging.warning(
                            f"  - Contact '{referee['personnamn']}' already in group or invalid group ID."
                        )
                    else:
                        raise
                except Exception as e:
                    logging.error("  - Error adding contact to 'Referees' group: %s", e)
            return contact_id  # Return contact id on success

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (contact creation), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                elif error.resp.status == 409:  # Conflict - contact already exists
                    logging.warning(
                        f"  - Contact for referee '{referee['personnamn']}' already exists (Conflict Error 409). Skipping creation, finding existing by phone for group add."
                    )
                    existing_contact = find_contact_by_phone(service, referee["mobiltelefon"])
                    if existing_contact:
                        return existing_contact[
                            "resourceName"
                        ]  # Return existing contact id on conflict

                    return None  # Failed to create or find existing in conflict case

                else:  # Quota exceeded, but max retries reached
                    logging.error(
                        f"Google People API Quota exceeded (contact creation), max retries reached. Error: {error}"
                    )
                    print(f"   Full error details (contact creation): {error.content.decode()}")
                    return None  # Return None on max retries
            elif (
                error.resp.status == 409
            ):  # 409 is conflict, contact already exists - handle gracefully
                logging.warning(
                    f"  - Contact for referee '{referee['personnamn']}' already exists (Conflict Error 409). Skipping creation, finding existing by phone."
                )
                existing_contact = find_contact_by_phone(service, referee["mobiltelefon"])
                if existing_contact:
                    return existing_contact[
                        "resourceName"
                    ]  # Return existing contact id on conflict
                else:
                    return None  # Failed to create or find existing in conflict case
            else:  # Other HTTP errors
                logging.error("An HTTP error occurred during contact creation: %s", error)
                print(f"   Full error details (contact creation): {error.content.decode()}")
                return None  # Return None for other errors
        except Exception as e:
            logging.exception("An unexpected error occurred while creating contact: %s", e)
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def test_google_contacts_connection(service):
    """Test the connection to Google People API."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            results = (
                service.people()
                .connections()
                .list(resourceName="people/me", personFields="names,phoneNumbers", pageSize=10)
                .execute()
            )

            connections = results.get("connections", [])
            if connections:
                logging.info(
                    "Connection established: Google People API is working and can access personal contacts!"
                )
                return True

            logging.warning(
                "Successfully connected to Google People API, but no contacts found in your list."
            )
            return True  # Still successful connection

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded (connection test), retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (connection test), max retries reached. Error: {error}"
                    )
                    print(f"   Full error details (connection test): {error.content.decode()}")
                    return False  # Return False if max retries reached
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error("HTTPError during People API test: %s", error)
                print(f"Full error details: {error.content.decode()}")
                return False  # Return False for other errors
        except Exception as e:
            logging.exception(
                f"An unexpected error occurred during People API connection test: {e}"
            )
            return False
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return False  # Return False if all retries fail
