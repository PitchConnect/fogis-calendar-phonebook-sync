#!/usr/bin/env python3
"""
Manual authentication restart script.

Use this script when you miss the 10-minute authentication window
and need to restart the authentication process.
"""

import json
import logging
import sys
from headless_auth import HeadlessAuthManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Restart the authentication process."""
    print("🔄 Restarting Authentication Process")
    print("=" * 50)
    
    try:
        # Create headless auth manager
        auth_manager = HeadlessAuthManager()
        
        # Check current token status
        token_status = auth_manager.get_token_status()
        
        print("📊 Current Token Status:")
        print(f"  Valid: {token_status.get('valid', False)}")
        print(f"  Expired: {token_status.get('expired', True)}")
        print(f"  Needs Refresh: {token_status.get('needs_refresh', True)}")
        
        if token_status.get('expiry'):
            print(f"  Expires: {token_status['expiry']}")
        
        print()
        
        # Ask user if they want to proceed
        if token_status.get('valid', False) and not token_status.get('needs_refresh', True):
            print("✅ Token is still valid and doesn't need refresh.")
            proceed = input("Do you still want to force re-authentication? [y/N]: ").strip().lower()
            if proceed not in ['y', 'yes']:
                print("ℹ️  Authentication restart cancelled.")
                return 0
        
        print("🚀 Starting new authentication session...")
        print("📧 You will receive a new email with a fresh 10-minute window.")
        print()
        
        # Force a refresh
        success = auth_manager.force_refresh()
        
        if success:
            print("✅ Authentication completed successfully!")
            print("✅ New token saved and ready for use.")
            print("✅ Background monitoring will continue automatically.")
        else:
            print("❌ Authentication failed.")
            print("💡 You can try running this script again.")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Authentication cancelled by user.")
        return 0
    except Exception as e:
        logger.exception(f"Error during authentication restart: {e}")
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
