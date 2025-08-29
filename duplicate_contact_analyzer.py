#!/usr/bin/env python3
"""
FOGIS Duplicate Contact Analyzer

This script analyzes Google Contacts for duplicates created by the FOGIS service
and provides options for cleanup and prevention.

Usage:
    python3 duplicate_contact_analyzer.py --scan
    python3 duplicate_contact_analyzer.py --scan --detailed
    python3 duplicate_contact_analyzer.py --test-normalization
"""

import argparse
import logging
import sys

from googleapiclient.discovery import build

from fogis_contacts import (
    authorize_google_people,
    find_duplicate_contacts,
    normalize_phone_number,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def test_phone_normalization():
    """Test phone number normalization with various formats."""
    print("📞 Testing Phone Number Normalization")
    print("=" * 50)

    test_cases = [
        # Swedish formats
        ("070-123 45 67", "Swedish mobile with dashes and spaces"),
        ("0701234567", "Swedish mobile without formatting"),
        ("+46 70 123 45 67", "Swedish mobile with country code and spaces"),
        ("+46701234567", "Swedish mobile with country code"),
        ("46701234567", "Swedish mobile with country code (no +)"),
        # Edge cases
        ("", "Empty string"),
        ("invalid", "Invalid phone number"),
        ("+1234567890123", "International number"),
        ("08-123 456 78", "Swedish landline"),
        # Common variations
        ("070 123 45 67", "Swedish mobile with spaces"),
        ("070.123.45.67", "Swedish mobile with dots"),
        ("(070) 123-45-67", "Swedish mobile with parentheses"),
    ]

    for phone, description in test_cases:
        normalized = normalize_phone_number(phone)
        print(f"Input:  {phone!r:20} ({description})")
        print(f"Output: {normalized!r:20}")
        print()


def scan_duplicates(detailed=False):
    """Scan for duplicate contacts in Google Contacts."""
    print("🔍 Scanning for Duplicate Contacts")
    print("=" * 50)

    # Authenticate with Google People API
    print("🔐 Authenticating with Google People API...")
    creds = authorize_google_people()
    if not creds:
        print("❌ Authentication failed. Please check your credentials.")
        return False

    # Build service
    service = build("people", "v1", credentials=creds)
    print("✅ Authentication successful")

    # Scan for duplicates
    print("\n🔍 Analyzing contacts for duplicates...")
    duplicate_report = find_duplicate_contacts(service, dry_run=True)

    if "error" in duplicate_report:
        print(f"❌ Error during duplicate scan: {duplicate_report['error']}")
        return False

    # Display summary
    print("\n📊 Duplicate Analysis Summary")
    print("-" * 30)
    print(f"Total contacts analyzed: {duplicate_report['total_contacts']}")
    print(f"Phone duplicate groups: {duplicate_report['phone_duplicate_groups']}")
    print(f"Email duplicate groups: {duplicate_report['email_duplicate_groups']}")
    print(f"FogisId duplicate groups: {duplicate_report['fogis_duplicate_groups']}")
    print(f"Total duplicate contacts: {duplicate_report['total_duplicate_contacts']}")

    if detailed and (
        duplicate_report["phone_duplicates"]
        or duplicate_report["email_duplicates"]
        or duplicate_report["fogis_duplicates"]
    ):
        print("\n📋 Detailed Duplicate Report")
        print("-" * 30)

        # Phone number duplicates
        if duplicate_report["phone_duplicates"]:
            print("\n📞 Phone Number Duplicates:")
            for phone, contacts in duplicate_report["phone_duplicates"].items():
                print(f"\n  📱 {phone}:")
                for i, contact in enumerate(contacts, 1):
                    print(f"    {i}. {contact['name']}")
                    print(f"       ID: {contact['id']}")
                    print(f"       Original phone: {contact['phone']}")

        # Email address duplicates
        if duplicate_report["email_duplicates"]:
            print("\n📧 Email Address Duplicates:")
            for email, contacts in duplicate_report["email_duplicates"].items():
                print(f"\n  📧 {email}:")
                for i, contact in enumerate(contacts, 1):
                    print(f"    {i}. {contact['name']}")
                    print(f"       ID: {contact['id']}")
                    print(f"       Original email: {contact['email']}")

        # FogisId duplicates
        if duplicate_report["fogis_duplicates"]:
            print("\n🆔 FogisId Duplicates:")
            for fogis_id, contacts in duplicate_report["fogis_duplicates"].items():
                print(f"\n  🏷️  {fogis_id}:")
                for i, contact in enumerate(contacts, 1):
                    print(f"    {i}. {contact['name']}")
                    print(f"       ID: {contact['id']}")

    # Provide recommendations
    print("\n💡 Recommendations")
    print("-" * 20)

    if duplicate_report["total_duplicate_contacts"] == 0:
        print("✅ No duplicates found! Your contacts are clean.")
    else:
        print("⚠️  Duplicates detected. Consider the following actions:")
        print("   1. Review the duplicate list above")
        print("   2. Manually merge or delete duplicates in Google Contacts")
        print("   3. The enhanced duplicate detection will prevent future duplicates")

        if duplicate_report["phone_duplicates"]:
            print("   4. Phone number duplicates suggest the bug has been fixed")
            print("      but existing duplicates need manual cleanup")

        if duplicate_report["email_duplicates"]:
            print("   5. Email address duplicates indicate contacts with same email")
            print("      Review carefully as these may be legitimate separate contacts")

        if duplicate_report["fogis_duplicates"]:
            print("   6. FogisId duplicates should not occur - investigate further")

    return True


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze and manage duplicate contacts in FOGIS Google Contacts"
    )
    parser.add_argument("--scan", action="store_true", help="Scan for duplicate contacts")
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed duplicate report (use with --scan)"
    )
    parser.add_argument(
        "--test-normalization", action="store_true", help="Test phone number normalization"
    )

    args = parser.parse_args()

    if not any([args.scan, args.test_normalization]):
        parser.print_help()
        return 1

    try:
        if args.test_normalization:
            test_phone_normalization()

        if args.scan:
            success = scan_duplicates(detailed=args.detailed)
            if not success:
                return 1

        return 0

    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.exception("Unexpected error in duplicate analyzer")
        return 1


if __name__ == "__main__":
    sys.exit(main())
