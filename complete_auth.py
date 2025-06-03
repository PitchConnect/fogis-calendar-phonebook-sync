#!/usr/bin/env python3
import json

from google_auth_oauthlib.flow import InstalledAppFlow


def main():
    """Complete OAuth authentication with hardcoded authorization response."""
    # Load config
    with open("config.json", "r") as f:
        config = json.load(f)

    scopes = config.get(
        "SCOPES",
        ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/contacts"],
    )

    # Create flow
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
    flow.redirect_uri = "http://localhost:8080/callback"

    # Complete the flow with authorization response
    authorization_response = "http://localhost:8080/callback?state=CdJuw0chqZcjvJuuXkWBpi5stuRbIt&code=4/0AUJR-x5MEnNaC-qrNTtXNccEiNgW88oyFXgehj4T8Ba8Vah14kewUQiK_stP6XaX9ZE4mQ&scope=https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/calendar"

    try:
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials

        # Save the token
        with open("token.json", "w") as token_file:
            token_file.write(credentials.to_json())

        print("✅ Authentication successful!")
        print("✅ Token saved to token.json")
        print(f"✅ Token expires: {credentials.expiry}")
        print(f"✅ Has refresh token: {bool(credentials.refresh_token)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
