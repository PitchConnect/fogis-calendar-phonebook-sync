#!/usr/bin/env python3
"""
Script to add headless authentication support to the main application.

This script modifies fogis_calendar_sync.py to support the --headless flag
and integrate with the headless authentication system.
"""

import os
import sys


def backup_original():
    """Create backup of original file."""
    original = "fogis_calendar_sync.py"
    backup = "fogis_calendar_sync.py.backup"

    if not os.path.exists(original):
        print(f"❌ {original} not found!")
        return False

    if not os.path.exists(backup):
        with open(original, "r") as src, open(backup, "w") as dst:
            dst.write(src.read())
        print(f"✅ Created backup: {backup}")
    else:
        print(f"ℹ️  Backup already exists: {backup}")

    return True


def add_headless_import():
    """Add headless authentication import."""
    import_line = """
# Headless authentication support
try:
    from headless_auth import integrate_with_existing_auth
    HEADLESS_AUTH_AVAILABLE = True
except ImportError:
    HEADLESS_AUTH_AVAILABLE = False
    print("⚠️  Headless authentication not available - missing modules")
"""

    with open("fogis_calendar_sync.py", "r") as f:
        content = f.read()

    # Find a good place to insert the import (after other imports)
    if "from fogis_contacts import" in content:
        insertion_point = content.find("from fogis_contacts import")
        # Find the end of this import block
        end_point = content.find("\n\n", insertion_point)
        if end_point == -1:
            end_point = content.find("\n#", insertion_point)

        if end_point != -1:
            new_content = content[:end_point] + import_line + content[end_point:]

            with open("fogis_calendar_sync.py", "w") as f:
                f.write(new_content)

            print("✅ Added headless authentication import")
            return True

    print("❌ Could not find suitable location for import")
    return False


def add_headless_argument():
    """Add --headless argument to argument parser."""
    with open("fogis_calendar_sync.py", "r") as f:
        content = f.read()

    # Find the argument parser section
    if "argparse.ArgumentParser" in content:
        # Look for where arguments are added
        parser_section = content.find("add_argument")
        if parser_section != -1:
            # Find a good insertion point (before parse_args())
            parse_args_point = content.find("parse_args()")
            if parse_args_point != -1:
                # Insert before parse_args()
                headless_arg = """
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Enable headless authentication mode for server environments"
    )
"""
                # Find the line before parse_args()
                lines = content[:parse_args_point].split("\n")
                insertion_line = len(lines) - 1

                # Insert the argument
                lines.insert(insertion_line, headless_arg.strip())
                new_content = "\n".join(lines) + content[parse_args_point:]

                with open("fogis_calendar_sync.py", "w") as f:
                    f.write(new_content)

                print("✅ Added --headless argument")
                return True

    print("❌ Could not find argument parser section")
    return False


def modify_auth_function():
    """Modify the authorize_google_calendar function to support headless mode."""
    with open("fogis_calendar_sync.py", "r") as f:
        content = f.read()

    # Find the authorize_google_calendar function
    func_start = content.find("def authorize_google_calendar():")
    if func_start == -1:
        print("❌ Could not find authorize_google_calendar function")
        return False

    # Find the end of the function (next def or end of file)
    func_end = content.find("\ndef ", func_start + 1)
    if func_end == -1:
        func_end = len(content)

    # Create new function with headless support
    new_func = '''def authorize_google_calendar(headless_mode=False):
    """Authorizes access to the Google Calendar API."""

    # Try headless authentication first if enabled
    if headless_mode and HEADLESS_AUTH_AVAILABLE:
        logging.info("Attempting headless authentication")
        creds = integrate_with_existing_auth(config_dict, headless_mode=True)
        if creds:
            logging.info("Headless authentication successful")
            return creds
        else:
            logging.warning("Headless authentication failed, falling back to standard method")

    # Original authentication logic
    creds = None
    logging.info("Starting Google Calendar authorization process")

    if os.path.exists("token.json"):
        try:
            logging.info("Token file exists, attempting to load. Scopes: %s", config_dict["SCOPES"])
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                "token.json", scopes=config_dict["SCOPES"]
            )
            logging.info("Successfully loaded Google Calendar credentials from token.json.")
        except Exception as e:
            logging.error("Error loading credentials from token.json: %s", e)
            logging.info("Will attempt to create new credentials")
            creds = None  # Ensure creds is None if loading fails

    # If there are no (valid) credentials available, let the user log in.
    if not creds:
        logging.info("No credentials found, will create new ones")
    elif not creds.valid:
        logging.info("Credentials found but not valid")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Credentials expired but have refresh token, attempting to refresh")
            try:
                creds.refresh(google.auth.transport.requests.Request())
                logging.info("Google Calendar credentials successfully refreshed")
                # Save the refreshed credentials
                with open("token.json", "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                logging.info("Refreshed credentials saved to token.json")
            except google.auth.exceptions.RefreshError as e:  # Catch refresh-specific errors
                logging.error(
                    f"Error refreshing Google Calendar credentials: {e}. Deleting token.json."
                )
                if os.path.exists("token.json"):
                    os.remove("token.json")
                    logging.info("Deleted invalid token.json file")
                creds = None  # Force re-authentication
            except Exception as e:
                logging.error(f"Unexpected error refreshing credentials: {e}")
                creds = None

        if not creds or not creds.valid:
            if headless_mode:
                logging.error("Cannot perform interactive authentication in headless mode")
                logging.error("Please run setup_headless_auth.py to configure headless authentication")
                return None

            # Interactive authentication (original code continues...)
'''

    # Replace the function
    new_content = content[:func_start] + new_func + content[func_end:]

    with open("fogis_calendar_sync.py", "w") as f:
        f.write(new_content)

    print("✅ Modified authorize_google_calendar function for headless support")
    return True


def add_main_integration():
    """Add headless mode integration to main function."""
    with open("fogis_calendar_sync.py", "r") as f:
        content = f.read()

    # Find where authorize_google_calendar is called
    auth_call = content.find("authorize_google_calendar()")
    if auth_call != -1:
        # Replace the call to include headless parameter
        new_call = "authorize_google_calendar(headless_mode=args.headless)"
        new_content = content.replace("authorize_google_calendar()", new_call)

        with open("fogis_calendar_sync.py", "w") as f:
            f.write(new_content)

        print("✅ Updated authorize_google_calendar call to support headless mode")
        return True

    print("❌ Could not find authorize_google_calendar() call")
    return False


def main():
    """Main function to add headless support."""
    print("🔧 Adding Headless Authentication Support")
    print("=" * 50)

    if not backup_original():
        return 1

    success = True

    if not add_headless_import():
        success = False

    if not add_headless_argument():
        success = False

    if not modify_auth_function():
        success = False

    if not add_main_integration():
        success = False

    if success:
        print("\n✅ Successfully added headless authentication support!")
        print("\nNext steps:")
        print("1. Run: python setup_headless_auth.py")
        print("2. Configure your email settings")
        print("3. Test with: python fogis_calendar_sync.py --headless")
    else:
        print("\n❌ Some modifications failed. Check the output above.")
        print("You may need to manually integrate the headless authentication.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
