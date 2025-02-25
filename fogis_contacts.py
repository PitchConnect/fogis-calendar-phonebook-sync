# fogis_contacts.py
import logging
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import json  # Ensure json is imported

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
    "https://www.googleapis.com/auth/contacts",  # Full read/write access to contacts
]

CREDENTIALS_FILE = "credentials.json"  # Added to be used in authorize_google_people, you can consider adding this to config.json later


def authorize_google_people(config):  # Moved from google_contacts_test.py and fogis_calendar_sync.py
    """Authorizes access to the Google People API."""
    creds = None
    if os.path.exists('token.json'):  # Load token from token.json
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json',
                                                                                    SCOPES)  # Load credentials to creds
            logging.info("Successfully loaded Google People credentials from token.json.")
        except Exception as e:
            logging.error(f"Error loading credentials from token.json: {e}")
            creds = None  # Ensure creds is None if loading fails

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:  # If no creds or creds not valid
        if creds and creds.expired and creds.refresh_token:  # If creds exist, but expired, try to refresh
            try:
                creds.refresh(google.auth.transport.requests.Request())
                logging.info("Google People credentials Refreshed")
            except Exception as e:
                logging.error(f"Error refreshing credentials: {e}")
                return None  # Exit, as we cannot refresh
        else:  # If no creds at all, run auth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            logging.info("New Google People Creds Auth Completed")

    return creds


def find_or_create_referees_group(service, config):
    """Finds the 'Referees' group or creates it if it doesn't exist."""
    group_name = "Referees"  # Define group name here - constant

    try:
        # List all contact groups
        results = service.contactGroups().list(
            pageSize=10,  # Adjust page size as needed
        ).execute()
        groups = results.get('contactGroups', [])
        logging.info("  - Contact groups fetched")

        # Check if 'Referees' group exists
        for group in groups:
            if group['name'] == group_name:
                logging.info(f"  - Existing '{group_name}' group found with ID: {group['resourceName']}")
                return group['resourceName']  # Return existing group's resource name

        logging.info(f"  - '{group_name}' group not found, creating...")

        # Group doesn't exist, create it
        group_body = {'contactGroup': {'name': group_name}}
        create_result = service.contactGroups().create(body=group_body).execute()
        new_group_id = create_result['resourceName']
        logging.info(f"  - Created new '{group_name}' group with ID: {new_group_id}")
        return new_group_id  # Return newly created group's resource name

    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        print(f"Full error details: {error.content.decode()}")  # Print full error details
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred while finding or creating group:")
        return None


def process_referees(match, config):  # Removed service arg, service is now build here
    """Manages referees contacts."""
    creds = authorize_google_people(config)  # Get creds here, in this scope.
    if not creds:  # If not creds, then exit out.
        logging.error("Failed to obtain Google People API credentials for referee processing.")
        return False

    try:  # Build the service inside process_referees, so that it's self-contained
        service = build('people', 'v1', credentials=creds)  # Build service here!

        for referee in match['domaruppdraglista']:
            name = referee['personnamn']
            phone = referee['mobiltelefon']
            try:
                existing_contact = find_contact_by_name_and_phone(service, name, phone, referee, config) # Pass referee data

                if existing_contact:
                    # Contact exists, check if needs updating
                    update_google_contact(service, existing_contact['resourceName'], referee, config)
                    logging.info(f"Updated contact for referee: {name}")
                else:
                    # Contact does not exist, create it
                    group_id = find_or_create_referees_group(service,
                                                             config)  # find group id here since service is built here.
                    if group_id:  # If group_id is valid
                        create_google_contact(service, referee, config, group_id)  # Create contact
                        logging.info(f"Created contact for referee: {name}")
                    else:  # Error if group_id is invalid
                        logging.error("Could not find group ID, skipping contact creationg")


            except Exception as e:
                logging.exception(f"An error occurred managing contact for referee {name}: {e}")
        return True  # Added return statement, to show that it ran, and did not fail
    except Exception as e:  # If service fails to build, then error out!
        logging.exception(f"An unexpected error occurred building people service: {e}")
        return False


def find_contact_by_name_and_phone(service, name, phone, referee, config):
    """Finds a contact in Google Contacts by domarNr, or fallback to phone number."""
    domar_nr = referee.get('domarnr') # Get domarnr from referee data

    # --- Lookup by externalId (FogisId=DomarNr) with Pagination ---
    if domar_nr:
        try:
            fogis_external_id_value = f"FogisId=DomarNr={domar_nr}" # Construct the expected externalId value

            all_connections = []  # List to store all connections across pages
            request = service.people().connections().list( # Initial request
                resourceName='people/me',
                personFields='names,phoneNumbers,externalIds',
                pageSize=100 # Keep pageSize, it's per page
            )
            while request: # Loop as long as there's a request (and nextPageToken)
                results = request.execute()
                connections = results.get('connections', [])
                all_connections.extend(connections) # Add current page's connections to the list
                request = service.people().connections().list_next(request, results) # Get request for next page

            if all_connections: # Now search within ALL connections
                for person in all_connections:
                    if 'externalIds' in person:
                        for externalId in person['externalIds']:
                            if externalId.get('type') == 'account' and externalId.get('value') == fogis_external_id_value: # Match by type and value
                                logging.info(f"  - Contact found by FogisId=DomarNr: {domar_nr}")
                                return person # Found by DomarNr
        except HttpError as error:
            logging.error(f"An HTTP error occurred during FogisId=DomarNr lookup (paginated): {error}")
            print(f"   Full error details (FogisId=DomarNr paginated lookup): {error.content.decode()}")
            return None
        except Exception as e:
            logging.exception(f"An unexpected error occurred during FogisId=DomarNr lookup (paginated): {e}")
            return None

    # --- Fallback Lookup by Phone Number with Pagination ---
    try:
        all_connections = [] # Reset for phone number lookup
        request = service.people().connections().list( # Initial request
            resourceName='people/me',
            personFields='names,phoneNumbers',
            pageSize=100
        )
        while request: # Loop for pagination
            results = request.execute()
            connections = results.get('connections', [])
            all_connections.extend(connections)
            request = service.people().connections().list_next(request, results)

        if all_connections: # Search within ALL connections
            for person in all_connections:
                if 'phoneNumbers' in person:
                    for phoneNumber in person['phoneNumbers']:
                        if phoneNumber['value'] == phone:
                            logging.info(f"  - Contact found by phone number (fallback, paginated): {phone}")
                            return person
        logging.info(f"  - Contact not found for name '{name}' and phone '{phone}' (paginated search)")
        return None # Not found by either method

    except HttpError as error:
        logging.error(f"An HTTP error occurred during phone number lookup (paginated): {error}")
        print(f"   Full error details (phone paginated lookup): {error.content.decode()}")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred during phone number lookup (paginated): {e}")
        return None


def update_google_contact(service, contact_id, referee, config):  # New function to delete contact
    """Deletes a contact from Google Contacts."""
    try:
        # 1. Retrieve the existing contact *and ETag*
        existing_contact = service.people().get(resourceName=contact_id,
                                                personFields='names,phoneNumbers,emailAddresses,organizations,addresses,notes,etag').execute()  # Get existing contact - request all fields
        existing_etag = existing_contact['etag']  # Extract ETag

        # Prepare updated contact data (for now, just update phone number if different)
        updated_names = existing_contact.get('names', [])
        updated_phone_numbers = existing_contact.get('phoneNumbers', [])
        updated_email_addresses = existing_contact.get('emailAddresses', [])  # Get existing emails
        updated_organizations = existing_contact.get('organizations', [])  # Get existing orgs
        updated_addresses = existing_contact.get('addresses', [])  # Get existing addresses

        # Update phone number if different
        if referee['mobiltelefon']:
            new_phone_number = {'value': referee['mobiltelefon'], 'type': 'mobile'}
            if not updated_phone_numbers or updated_phone_numbers[0].get('value') != referee[
                'mobiltelefon']:  # Basic check, improve as needed
                updated_phone_numbers = [new_phone_number]  # Replace with new number

        updated_contact_data = {  # Updated contact data body - Include ETag!
            'etag': existing_etag,  # Include ETag here!
            'person': {  # ADDED 'person' LEVEL - IMPORTANT
                'names': updated_names,
                'phoneNumbers': updated_phone_numbers,
                'emailAddresses': updated_email_addresses,  # ADDED emailAddresses
                'organizations': updated_organizations,  # ADDED organizations
                'addresses': updated_addresses,  # ADDED addresses
                'notes': existing_contact.get('notes')  # Carry over existing notes
            }
        }

        # 3. Update the contact
        updated_person = service.people().updateContact(
            resourceName=contact_id,
            body=updated_contact_data,
            updatePersonFields='names,phoneNumbers,emailAddresses,organizations,addresses,notes'  # Update all fields
        ).execute()

        logging.info(f"  - Updated contact for referee: {referee['personnamn']} with ID: {contact_id}")
        return contact_id  # Return updated contact ID

    except HttpError as error:
        logging.error(f"An HTTP error occurred updating contact {contact_id}: {error}")
        print(f"   Full error details: {error.content.decode()}")  # Print full error details
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred while updating contact: {e}")
        return None


def create_contact_data(referee, match_date_str=None):  # Added match_date_str parameter
    """Creates a Google Contact data structure from referee information."""
    contact_data = {
        "names": [
            {
                "displayName": referee['personnamn'],
                "givenName": referee['personnamn'].split()[0] if referee['personnamn'] else "",
                # Splits name into first name
                "familyName": referee['personnamn'].split()[-1] if referee['personnamn'] else ""
                # Splits name into last name
            }
        ],
        "phoneNumbers": [
            {
                "value": referee['mobiltelefon'],
                "type": "mobile"
            }
        ],
        "emailAddresses": [
            {
                "value": referee['epostadress'],
                "type": "work"  # Work email
            }
        ],
        "addresses": [
            {
                "formattedValue": f"{referee['adress']}, {referee['postnr']} {referee['postort']}, {referee['land']}",
                # Full address
                "streetAddress": referee['adress'],  # Street address
                "postalCode": referee['postnr'],  # Postal code
                "city": referee['postort'],  # City
                "country": referee['land'],  # Country
                "type": "home"  # Home address type
            }
        ],
        "externalIds": [  # Add externalIds section
            {
                "value": f"FogisId=DomarNr={referee['domarnr']}", # Use DomarNr and prepend "FogisId=DomarNr="
                "type": "account" # You can use "account" or "custom" as type
            }
        ]
    }

    if match_date_str:  # Important dates section only if date is given
        contact_data["importantDates"] = [
            {
                "label": "Refereed Until",  # Label of important date
                "dateTime": {  # Date object
                    "year": int(match_date_str.split('-')[0]),  # Extracting year from match_date_str
                    "month": int(match_date_str.split('-')[1]),  # Extracting month from match_date_str
                    "day": int(match_date_str.split('-')[2])  # Extracting day from match_date_str
                },
                "type": "other"  # Important dates type
            }]

    # Handle empty fields - remove empty fields to avoid errors and keep contact clean
    contact_data["phoneNumbers"] = [number for number in contact_data.get("phoneNumbers", []) if
                                    number.get("value")]  # Phone numbers
    contact_data["emailAddresses"] = [email for email in contact_data.get("emailAddresses", []) if
                                      email.get("value")]  # Email addresses
    contact_data["organizations"] = [org for org in contact_data.get("organizations", []) if
                                     org.get("title")]  # Organisations
    contact_data["addresses"] = [addr for addr in contact_data.get("addresses", []) if
                                 addr.get("formattedValue")]  # Addresses
    contact_data["externalIds"] = [ext_id for ext_id in contact_data.get("externalIds", []) if ext_id.get("value")] # Ensure externalIds are valid

    return contact_data


def find_contact_by_phone(service, phone, config):  # Renamed to find_contact_by_phone
    """Finds a contact in Google Contacts by phone number."""
    try:
        # List all connections
        results = service.people().connections().list(
            resourceName='people/me',
            personFields='names,phoneNumbers',
            pageSize=100  # Adjust as needed, up to 1000
        ).execute()
        connections = results.get('connections', [])

        if connections:
            for person in connections:
                if 'phoneNumbers' in person:
                    for phoneNumber in person['phoneNumbers']:
                        if phoneNumber['value'] == phone:
                            logging.info(f"  - Existing contact found for phone number: {phone}")
                            return person  # Return person if found
        return None  # Return None if not found

    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        print(f"   Full error details: {error.content.decode()}")  # Print full error details
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred in find_contact_by_phone(): {e}")
        return None


def create_google_contact(service, referee, config, group_id):  # Added match_date_str
    """Creates a new contact in Google Contacts and adds it to the specified group."""

    contact_data = create_contact_data(referee)  # Reuse function

    try:
        # Create the contact
        person = service.people().createContact(body=contact_data).execute()
        contact_id = person['resourceName']
        logging.info(f"  - Created contact for referee: {referee['personnamn']} with ID: {contact_id}")

        # Add contact to the "Referees" group
        if group_id:  # Double check group_id is valid
            try:
                session = service.contactGroups().members().modify(
                    resourceName=group_id,
                    body={'resourceNamesToAdd': [contact_id]}  # Adds the new contact id
                ).execute()
                logging.info(f"  - Added contact '{referee['personnamn']}' to 'Referees' group.")
            except HttpError as e:
                if e.resp.status == 400:
                    logging.warning(f"  - Contact '{referee['personnamn']}' already in group or invalid group ID.")
                else:
                    raise  # Re-raise other HTTP errors
            except Exception as e:
                logging.error(f"  - Error adding contact to 'Referees' group: {e}")

        return contact_id  # Return newly created contact's resource name

    except HttpError as error:
        if error.resp.status == 409:  # 409 error code is for "Conflict"
            logging.warning(
                f"  - Contact for referee '{referee['personnamn']}' already exists (Conflict Error 409). фи Skipping creation.")
            existing_contact = find_contact_by_phone(service, referee['mobiltelefon'],
                                                     config)  # Find existing contact (reuse function)
            if existing_contact:
                return existing_contact['resourceName']  # Return existing contact's resource name
            else:
                return None  # Failed to create or find existing

        else:  # Other http errors
            logging.error(f"An HTTP error occurred: {error}")
            print(f"   Full error details: {error.content.decode()}")  # Print full error details
            return None
    except Exception as e:  # Other errors
        logging.exception(f"An unexpected error occurred while creating contact:")
        return None


def test_google_contacts_connection(service, config):
    """Test the connection to Google People API using connections().list for personal contacts."""
    try:
        # List the user's connections (personal contacts) - CORRECT METHOD IS NOW USED!
        results = service.people().connections().list(
            resourceName='people/me',
            personFields='names,phoneNumbers',
            pageSize=10  # Adjust pageSize as needed, keep it small for testing
        ).execute()

        connections = results.get('connections', [])
        if connections:
            logging.info(
                f"Connection established: Google People API is working and can access personal contacts!")  # Updated success log message - more accurate
            return True
        else:
            logging.warning("Successfully connected to Google People API, but no contacts found in your list.")
            return True  # Still successful connection

    except HttpError as error:
        logging.error(f"HTTPError during People API test: {error}")
        print(f"Full error details: {error.content.decode()}")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred during People API connection test:")
        return False