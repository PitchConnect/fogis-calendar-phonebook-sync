#!/usr/bin/env python3
"""
Clean authentication script that bypasses all our custom code
and uses the Google OAuth library directly.
"""

import json
import os
import sys

# Set environment variable to allow HTTP for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def main():
    """Perform clean Google authentication."""
    print("🔐 Clean Google Authentication")
    print("=" * 40)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)

        scopes = config.get('SCOPES', [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/contacts',
            'https://www.googleapis.com/auth/drive'
        ])

        print("Required scopes:")
        for scope in scopes:
            print(f"  - {scope}")
        print()

        # Create flow with minimal parameters
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            scopes
        )

        # Use the built-in run_local_server method which handles everything
        print("🚀 Starting local server for authentication...")
        print("📱 Your browser will open automatically")
        print("🔐 Complete the authentication in your browser")
        print()

        # This method handles everything automatically
        credentials = flow.run_local_server(
            port=8080,
            prompt='consent',
            access_type='offline'
        )

        # Save the token
        with open('token.json', 'w') as token_file:
            token_file.write(credentials.to_json())

        print()
        print("✅ Authentication successful!")
        print("✅ Token saved to token.json")
        print(f"✅ Token expires: {credentials.expiry}")
        print(f"✅ Has refresh token: {bool(credentials.refresh_token)}")
        print()
        print("🎉 All Google services can now use this token!")
        print("   - Calendar Sync ✅")
        print("   - Contacts Sync ✅")
        print("   - Google Drive Service ✅")

        return 0

    except ImportError as e:
        print(f"❌ Missing required library: {e}")
        print("💡 Try: pip install google-auth-oauthlib")
        return 1
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("💡 Make sure credentials.json and config.json exist")
        return 1
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check your internet connection and try again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
