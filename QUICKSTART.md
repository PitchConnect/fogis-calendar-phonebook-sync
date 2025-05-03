# FOGIS Calendar & Contacts Sync - Quick Start Guide

This guide will help you quickly set up and run the FOGIS Calendar & Contacts Sync tool on a new computer.

## Prerequisites

- Python 3.6 or higher
- A Google account with access to Google Calendar and Google Contacts
- A FOGIS account with access to your match schedule
- Google Cloud project with Calendar API and People API enabled

## Quick Setup

1. **Run the setup script**

   ```bash
   python setup.py
   ```

   This interactive script will:
   - Check for required files
   - Help you set up a virtual environment
   - Install required dependencies
   - Guide you through setting up environment variables
   - Test connections to Google APIs and FOGIS

2. **Set up Google API credentials**

   If you don't have `credentials.json`:
   
   a. Go to the [Google Cloud Console](https://console.cloud.google.com/)
   b. Create a new project or select an existing one
   c. Enable the Google Calendar API and Google People API
   d. Create OAuth 2.0 credentials (Desktop application)
   e. Download the credentials as JSON
   f. Rename the file to `credentials.json` and place it in the project directory

3. **Configure your calendar**

   Make sure your `config.json` has the correct Calendar ID:
   
   ```json
   {
     "CALENDAR_ID": "your_calendar_id@group.calendar.google.com",
     ...
   }
   ```
   
   You can find your Calendar ID in Google Calendar:
   - Go to Settings for the calendar
   - Scroll down to "Integrate calendar"
   - Copy the Calendar ID

4. **Set up FOGIS credentials**

   Create a `.env` file with your FOGIS credentials:
   
   ```
   FOGIS_USERNAME=your_fogis_username
   FOGIS_PASSWORD=your_fogis_password
   ```

   Or use the setup script to create this file for you.

5. **Run the sync**

   ```bash
   python fogis_calendar_sync.py
   ```

   The first time you run this, it will open a browser window for Google authentication.

## Troubleshooting

- **Authentication errors**: Delete `token.json` (if it exists) and run the script again
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **FOGIS login errors**: Check your username and password in the `.env` file
- **Calendar sync issues**: Verify your Calendar ID in `config.json`

For more detailed information, refer to the full [README.md](README.md).
