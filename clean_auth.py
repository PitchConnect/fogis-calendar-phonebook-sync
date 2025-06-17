#!/usr/bin/env python3
"""
Clean authentication script that bypasses all our custom code
and uses the Google OAuth library directly.
"""

import json
import os
import sys

# Set environment variable to allow HTTP for localhost
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def main():
    """Perform clean Google authentication."""
    print("🔐 Clean Google Authentication")
    print("=" * 40)

    try:
        from google_auth_oauthlib.flow import Flow

        # Load config
        with open("config.json", "r") as f:
            config = json.load(f)

        scopes = config.get(
            "SCOPES",
            [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
                "https://www.googleapis.com/auth/drive",
            ],
        )

        print("Required scopes:")
        for scope in scopes:
            print(f"  - {scope}")
        print()

        # Create flow with explicit redirect URI for web application flow
        redirect_uri = "http://localhost:8080/callback"
        flow = Flow.from_client_secrets_file("credentials.json", scopes, redirect_uri=redirect_uri)

        # Generate authorization URL
        print("🚀 Starting OAuth flow...")
        print("🔐 Complete the authentication in your browser")
        print()

        # Generate authorization URL
        auth_url, state = flow.authorization_url(
            access_type="offline", prompt="consent", include_granted_scopes="true"
        )

        print("🔗 Please visit this URL to authorize the application:")
        print(auth_url)
        print()
        print("📋 After authorization, copy the full callback URL from your browser")
        print("   (it should start with http://localhost:8080/callback?...)")
        print()

        # Get authorization response from user
        callback_url = input("📥 Paste the full callback URL here: ").strip()

        # Exchange authorization code for credentials
        flow.fetch_token(authorization_response=callback_url)
        credentials = flow.credentials

        # Save the token
        with open("token.json", "w") as token_file:
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
