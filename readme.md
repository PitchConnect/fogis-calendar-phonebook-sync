# FOGIS Calendar Sync for Home Assistant

This script synchronizes match data from FOGIS (the Swedish Football Association's online system) with your Google Calendar.

## Prerequisites

*   Home Assistant OS
*   Python 3
*   A Google Calendar
*   A FOGIS account

## Installation

1.  **Clone the repository:**

   ```bash
   git clone https://github.com/timmybird/FogisCalendarPhoneBookSync
   ```

2.  **Move the `fogis_calendar_sync.py` script:**

   Move the `fogis_calendar_sync.py` script to the `/config/python_scripts/fogis/` directory in your Home Assistant configuration. Create the `fogis` directory if it doesn't exist.

3.  **Install the required Python packages:**

   Navigate to the directory where you cloned the repository and run the following command to install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

   You may need to install `pip` first if it's not already installed:

   ```bash
   python3 -m ensurepip
   python3 -m pip install --upgrade pip
   ```

4.  **Configure Home Assistant:**

   *   Enable the `python_script` integration by adding the following to your `configuration.yaml` file:

      ```yaml
      python_script:
      ```

   *   Create an automation to trigger the Python script on a schedule. Add the following to your `configuration.yaml` file:

      ```yaml
      automation:
        - alias: Sync FOGIS Calendar
          trigger:
            - platform: time_pattern
              # Run every hour
              hours: "*"
              minutes: 0
              seconds: 0
          action:
            - service: python_script.fogis.fogis_calendar_sync
              data:
                username: "{{ secrets.fogis_username }}"
                password: "{{ secrets.fogis_password }}"
      ```

   *   Define your FOGIS username and password in your `secrets.yaml` file:

   ```yaml
    fogis_username: your_fogis_username
    fogis_password: your_fogis_password
   ```

5.  **Restart Home Assistant:**

   Restart Home Assistant for the changes to take effect.

## Configuration

*   **`config.json`:** This file contains the configuration parameters for the script, such as the Google Calendar ID, API keys, and URLs. Make sure to configure this file according to your needs.

## Usage

Once the script is installed and configured, it will automatically synchronize match data from FOGIS with your Google Calendar on the schedule you defined in the automation.

## Troubleshooting

*   **Script not running:** Check the Home Assistant logs for any errors related to the script or the `python_script` integration.
*   **Calendar not updating:** Verify that the Google Calendar ID is correct and that the script has the necessary permissions to access your calendar.
*   **FOGIS login failing:** Double-check your FOGIS username and password.

## Contributing

Contributions are welcome! Please submit a pull request with your changes.

## License

[MIT License](LICENSE)