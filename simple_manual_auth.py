#!/usr/bin/env python3
"""
Simple manual authentication - just generates URL and processes callback.
"""

import json
import os

# Set environment variable to allow HTTP for localhost
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def main():
    """Simple manual authentication."""
    print("🔐 Simple Manual Google Authentication")
    print("=" * 45)
    
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        # Load config
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        scopes = config.get('SCOPES')
        print("Required scopes:")
        for scope in scopes:
            print(f"  - {scope}")
        print()
        
        # Create flow
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
        
        # Use a simple redirect URI that will show an error page (but we'll get the code)
        flow.redirect_uri = 'http://localhost:1'
        
        # Generate auth URL
        auth_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        print("🔗 Authentication URL:")
        print(auth_url)
        print()
        print("📋 Instructions:")
        print("1. Copy the URL above and open it in your browser")
        print("2. Complete Google authentication")
        print("3. You'll get an error page - that's expected!")
        print("4. Copy the 'code' parameter from the error page URL")
        print("5. Paste the code below")
        print()
        
        # Get the authorization code
        auth_code = input("📥 Paste the authorization code here: ").strip()
        
        # Exchange code for token
        flow.fetch_token(code=auth_code)
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
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
