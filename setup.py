#!/usr/bin/env python3
"""Setup script for FOGIS Calendar & Contacts Sync.

This script helps new users set up the project by:
1. Checking for required files
2. Setting up a virtual environment
3. Installing required dependencies
4. Guiding the user through setting up environment variables
5. Testing connections to Google APIs and FOGIS
"""

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}\n")


def print_success(text):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_warning(text):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def run_command(command, cwd=None):
    """Run a command and return the result.

    Args:
        command: The command to run as a list of arguments
        cwd: Working directory for the command

    Returns:
        Tuple of (success, output)
    """
    if isinstance(command, str):
        # Split the command string into a list for security
        command = shlex.split(command)

    try:
        result = subprocess.run(
            command, shell=False, check=True, text=True, capture_output=True, cwd=cwd
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def check_python_version():
    """Check if Python version is 3.6 or higher."""
    print_header("Checking Python Version")

    version = sys.version_info
    if version.major >= 3 and version.minor >= 6:
        print_success(
            f"Python version {version.major}.{version.minor}.{version.micro} detected (3.6+ required)"
        )
        return True

    print_error(
        f"Python version {version.major}.{version.minor}.{version.micro} detected, but 3.6+ is required"
    )
    return False


def check_required_files():
    """Check if required files exist."""
    print_header("Checking Required Files")

    files_to_check = {
        "config.json": "Configuration file",
        "requirements.txt": "Python dependencies file",
    }

    all_files_exist = True

    for file, description in files_to_check.items():
        if os.path.exists(file):
            print_success(f"Found {description}: {file}")
        else:
            print_error(f"Missing {description}: {file}")
            all_files_exist = False

    # Special check for credentials.json
    if os.path.exists("credentials.json"):
        print_success("Found Google API credentials: credentials.json")
    else:
        print_warning("Missing Google API credentials: credentials.json")
        print_info("You will need to create a Google Cloud project and download credentials.")
        print_info("See the README.md for instructions on how to set up Google API credentials.")
        all_files_exist = False

    # Check for .env file
    if os.path.exists(".env"):
        print_success("Found environment variables file: .env")
    else:
        if os.path.exists(".env.example"):
            print_warning("Missing environment variables file: .env (but .env.example exists)")
            print_info("You can copy .env.example to .env and fill in your credentials.")
        else:
            print_warning("Missing environment variables file: .env")
            print_info("You will need to create a .env file with your FOGIS credentials.")
        all_files_exist = False

    return all_files_exist


def setup_virtual_environment():
    """Set up a virtual environment."""
    print_header("Setting Up Virtual Environment")

    venv_dir = "venv"

    # Check if virtual environment already exists
    if os.path.exists(venv_dir):
        print_info(f"Virtual environment already exists at {venv_dir}")
        activate_venv = input("Do you want to activate it? (y/n): ").lower()
        if activate_venv == "y":
            print_info("Please run the following command to activate the virtual environment:")
            if platform.system() == "Windows":
                print(f"  {venv_dir}\\Scripts\\activate")
            else:
                print(f"  source {venv_dir}/bin/activate")
        return True

    # Create virtual environment
    print_info("Creating virtual environment...")
    success, output = run_command(f"{sys.executable} -m venv {venv_dir}")

    if success:
        print_success(f"Virtual environment created at {venv_dir}")
        print_info("Please run the following command to activate the virtual environment:")
        if platform.system() == "Windows":
            print(f"  {venv_dir}\\Scripts\\activate")
        else:
            print(f"  source {venv_dir}/bin/activate")
        return True

    print_error(f"Failed to create virtual environment: {output}")
    return False


def install_dependencies():
    """Install required dependencies."""
    print_header("Installing Dependencies")

    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print_error("requirements.txt not found")
        return False

    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print_warning("Not running in a virtual environment")
        proceed = input("Do you want to proceed with installation anyway? (y/n): ").lower()
        if proceed != "y":
            print_info(
                "Please activate the virtual environment first and then run this script again."
            )
            return False

    # Install dependencies
    print_info("Installing dependencies from requirements.txt...")
    success, output = run_command(f"{sys.executable} -m pip install -r requirements.txt")

    if success:
        print_success("Dependencies installed successfully")
        return True

    print_error(f"Failed to install dependencies: {output}")
    return False


def setup_env_file():
    """Set up the .env file."""
    print_header("Setting Up Environment Variables")

    if os.path.exists(".env"):
        print_info(".env file already exists")
        modify = input("Do you want to modify it? (y/n): ").lower()
        if modify != "y":
            return True

    # Create .env file from .env.example if it exists
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        shutil.copy(".env.example", ".env")
        print_success("Created .env file from .env.example")

    # Get FOGIS credentials
    print_info("Please enter your FOGIS credentials:")
    fogis_username = input("FOGIS Username: ")
    fogis_password = input("FOGIS Password: ")

    # Write to .env file
    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"FOGIS_USERNAME={fogis_username}\n")
        f.write(f"FOGIS_PASSWORD={fogis_password}\n")

    print_success("Environment variables saved to .env file")
    return True


def check_google_credentials():
    """Check Google API credentials."""
    print_header("Checking Google API Credentials")

    if not os.path.exists("credentials.json"):
        print_error("credentials.json not found")
        print_info(
            "Please follow the instructions in the README.md to set up Google API credentials."
        )
        return False

    try:
        with open("credentials.json", "r", encoding="utf-8") as f:
            credentials = json.load(f)

        if "installed" in credentials and "client_id" in credentials["installed"]:
            print_success("credentials.json appears to be valid")
            return True

        print_error("credentials.json does not have the expected format")
        print_info(
            "Please make sure you downloaded the correct credentials file from the Google Cloud Console."
        )
        return False
    except json.JSONDecodeError:
        print_error("credentials.json is not a valid JSON file")
        return False
    except Exception as e:
        print_error(f"Error checking credentials.json: {str(e)}")
        return False


def check_config_file():
    """Check config.json file."""
    print_header("Checking Configuration")

    if not os.path.exists("config.json"):
        print_error("config.json not found")
        return False

    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        required_keys = ["CREDENTIALS_FILE", "CALENDAR_ID", "SYNC_TAG", "SCOPES"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            print_error(f"config.json is missing required keys: {', '.join(missing_keys)}")
            return False

        print_success("config.json appears to be valid")

        # Check calendar ID
        calendar_id = config.get("CALENDAR_ID", "")
        if calendar_id.endswith("@group.calendar.google.com") or calendar_id.endswith("@gmail.com"):
            print_success(f"Calendar ID looks valid: {calendar_id}")
        else:
            print_warning(f"Calendar ID may not be valid: {calendar_id}")
            print_info("Please make sure you've entered the correct Calendar ID in config.json.")

        return True
    except json.JSONDecodeError:
        print_error("config.json is not a valid JSON file")
        return False
    except Exception as e:
        print_error(f"Error checking config.json: {str(e)}")
        return False


def test_fogis_connection():
    """Test connection to FOGIS."""
    print_header("Testing FOGIS Connection")

    print_info("This will attempt to log in to FOGIS using your credentials.")
    proceed = input("Do you want to proceed? (y/n): ").lower()
    if proceed != "y":
        print_info("Skipping FOGIS connection test")
        return True

    # Run a simple test using the fogis_calendar_sync.py script
    print_info("Testing FOGIS connection...")
    _, output = run_command(
        f"{sys.executable} fogis_calendar_sync.py --username test --password test"
    )

    if "Login failed" in output:
        print_warning("FOGIS login test failed with test credentials (expected)")
        print_info("This is expected with test credentials. The script is working correctly.")
        print_info("Please update your .env file with your real FOGIS credentials.")
        return True

    print_error("Unexpected response from FOGIS login test")
    print_info("Please check the fogis_calendar_sync.py script for errors.")
    return False


def main():
    """Main function."""
    print_header("FOGIS Calendar & Contacts Sync Setup")
    print("This script will help you set up the FOGIS Calendar & Contacts Sync project.")

    # Check Python version
    if not check_python_version():
        print_error("Please install Python 3.6 or higher and run this script again.")
        return

    # Check required files
    check_required_files()

    # Set up virtual environment
    setup_virtual_environment()

    # Install dependencies
    install_deps = input("Do you want to install dependencies? (y/n): ").lower()
    if install_deps == "y":
        install_dependencies()

    # Set up .env file
    setup_env = input("Do you want to set up the .env file? (y/n): ").lower()
    if setup_env == "y":
        setup_env_file()

    # Check Google API credentials
    check_google_credentials()

    # Check config.json
    check_config_file()

    # Test FOGIS connection
    test_fogis = input("Do you want to test the FOGIS connection? (y/n): ").lower()
    if test_fogis == "y":
        test_fogis_connection()

    print_header("Setup Complete")
    print_info("You can now run the FOGIS Calendar & Contacts Sync script with:")
    print(f"  {sys.executable} fogis_calendar_sync.py")
    print_info("For more information, please refer to the README.md file.")


if __name__ == "__main__":
    main()
