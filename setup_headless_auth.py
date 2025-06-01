#!/usr/bin/env python3
"""
Setup Script for Headless Authentication

This script helps configure the headless authentication system for
long-term container operation.
"""

import getpass
import json
import os
import sys
from typing import Dict


def load_config() -> Dict:
    """Load existing configuration."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found!")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error reading config.json: {e}")
        return {}


def save_config(config: Dict):
    """Save configuration to file."""
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        print("✅ Configuration saved to config.json")
    except Exception as e:
        print(f"❌ Error saving config.json: {e}")


def setup_email_notifications(config: Dict):
    """Setup email notification configuration."""
    print("\n📧 Email Notification Setup")
    print("=" * 40)

    current_sender = config.get("NOTIFICATION_EMAIL_SENDER", "")
    current_receiver = config.get("NOTIFICATION_EMAIL_RECEIVER", "")

    print(f"Current sender: {current_sender}")
    print(f"Current receiver: {current_receiver}")

    sender = input(f"Email sender [{current_sender}]: ").strip()
    if sender:
        config["NOTIFICATION_EMAIL_SENDER"] = sender
        config["SMTP_USERNAME"] = sender  # Usually the same

    receiver = input(f"Email receiver [{current_receiver}]: ").strip()
    if receiver:
        config["NOTIFICATION_EMAIL_RECEIVER"] = receiver

    # SMTP settings
    smtp_server = input(f"SMTP server [{config.get('SMTP_SERVER', 'smtp.gmail.com')}]: ").strip()
    if smtp_server:
        config["SMTP_SERVER"] = smtp_server

    smtp_port = input(f"SMTP port [{config.get('SMTP_PORT', 587)}]: ").strip()
    if smtp_port:
        try:
            config["SMTP_PORT"] = int(smtp_port)
        except ValueError:
            print("⚠️  Invalid port number, keeping current value")

    # App password
    print("\n🔑 Gmail App Password Setup:")
    print("1. Go to https://myaccount.google.com/apppasswords")
    print("2. Generate an app password for 'Mail'")
    print("3. Enter the 16-character password below")

    app_password = getpass.getpass("Gmail app password (hidden): ").strip()
    if app_password:
        config["SMTP_PASSWORD"] = app_password
        print("✅ App password saved")
    else:
        print("⚠️  No app password entered - you'll need to set this manually")


def setup_auth_server(config: Dict):
    """Setup authentication server configuration."""
    print("\n🌐 Authentication Server Setup")
    print("=" * 40)

    current_host = config.get("AUTH_SERVER_HOST", "localhost")
    current_port = config.get("AUTH_SERVER_PORT", 8080)

    print(f"Current host: {current_host}")
    print(f"Current port: {current_port}")

    host = input(f"Auth server host [{current_host}]: ").strip()
    if host:
        config["AUTH_SERVER_HOST"] = host

    port = input(f"Auth server port [{current_port}]: ").strip()
    if port:
        try:
            config["AUTH_SERVER_PORT"] = int(port)
        except ValueError:
            print("⚠️  Invalid port number, keeping current value")


def check_credentials_file():
    """Check if Google credentials file exists."""
    print("\n🔐 Google Credentials Check")
    print("=" * 40)

    creds_file = "credentials.json"
    if os.path.exists(creds_file):
        print(f"✅ Found {creds_file}")
        return True
    else:
        print(f"❌ {creds_file} not found!")
        print("\nTo set up Google credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Calendar API and Google Contacts API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download the JSON file and save as 'credentials.json'")
        return False


def test_configuration():
    """Test the headless authentication configuration."""
    print("\n🧪 Testing Configuration")
    print("=" * 40)

    try:
        from headless_auth import HeadlessAuthManager

        auth_manager = HeadlessAuthManager()
        token_status = auth_manager.get_token_status()

        print(f"Token valid: {token_status.get('valid', False)}")
        print(f"Token expired: {token_status.get('expired', True)}")
        print(f"Needs refresh: {token_status.get('needs_refresh', True)}")

        if token_status.get("expiry"):
            print(f"Token expiry: {token_status['expiry']}")

        if not token_status.get("valid", False):
            print("\n⚠️  No valid token found - you'll need to authenticate")
            print("Run the application with --headless flag to start authentication")
        else:
            print("✅ Token is valid!")

    except ImportError as e:
        print(f"❌ Error importing headless auth modules: {e}")
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")


def main():
    """Main setup function."""
    print("🚀 FOGIS Calendar Sync - Headless Authentication Setup")
    print("=" * 60)

    # Load existing config
    config = load_config()
    if not config:
        print("❌ Could not load configuration. Please check config.json")
        return 1

    # Check credentials file
    has_credentials = check_credentials_file()

    # Setup email notifications
    setup_email = input("\nSetup email notifications? [y/N]: ").strip().lower()
    if setup_email in ["y", "yes"]:
        setup_email_notifications(config)

    # Setup auth server
    setup_server = input("\nSetup authentication server? [y/N]: ").strip().lower()
    if setup_server in ["y", "yes"]:
        setup_auth_server(config)

    # Save configuration
    save_config(config)

    # Test configuration
    test_config = input("\nTest configuration? [Y/n]: ").strip().lower()
    if test_config not in ["n", "no"]:
        test_configuration()

    print("\n🎉 Setup Complete!")
    print("=" * 40)

    if has_credentials:
        print("✅ Ready for headless authentication")
        print("\nNext steps:")
        print("1. Run your application with --headless flag")
        print("2. Check your email for authentication links")
        print("3. Complete authentication in your browser")
        print("4. Your container will run indefinitely!")
    else:
        print("⚠️  Please add Google credentials file first")
        print("Then re-run this setup script")

    return 0


if __name__ == "__main__":
    sys.exit(main())
