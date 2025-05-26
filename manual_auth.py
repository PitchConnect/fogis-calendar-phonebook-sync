#!/usr/bin/env python3
"""
Manual authentication script to create a token with all required scopes.
This bypasses the duplicate state parameter issue.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    """Create authentication token manually."""
    print("🔐 Manual Authentication for All Google Services")
    print("=" * 50)
    
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
    
    # Create flow
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
    flow.redirect_uri = 'http://localhost:8080/callback'
    
    # Generate clean auth URL
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    
    print("🔗 Authentication URL:")
    print(auth_url)
    print()
    print("📋 Instructions:")
    print("1. Copy the URL above and paste it in your browser")
    print("2. Complete Google authentication")
    print("3. Copy the FULL callback URL from your browser")
    print("4. Paste it below when prompted")
    print()
    
    # Get authorization response from user
    callback_url = input("📥 Paste the full callback URL here: ").strip()
    
    try:
        # Complete the flow
        flow.fetch_token(authorization_response=callback_url)
        credentials = flow.credentials
        
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
        print("   - Calendar Sync")
        print("   - Contacts Sync") 
        print("   - Google Drive Service")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
