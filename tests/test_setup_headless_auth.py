"""Tests for setup_headless_auth module."""

import json
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

import setup_headless_auth


class TestLoadConfig:
    """Test cases for the load_config function."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    @patch("builtins.print")
    def test_load_config_success(self, mock_print, mock_file):
        """Test successful config loading."""
        result = setup_headless_auth.load_config()

        assert result == {"test": "data"}
        mock_file.assert_called_once_with("config.json", "r")
        mock_print.assert_not_called()

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    @patch("builtins.print")
    def test_load_config_file_not_found(self, mock_print, mock_file):
        """Test config loading when file doesn't exist."""
        result = setup_headless_auth.load_config()

        assert result == {}
        mock_file.assert_called_once_with("config.json", "r")
        mock_print.assert_called_once_with("❌ config.json not found!")

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": json}')
    @patch("builtins.print")
    def test_load_config_invalid_json(self, mock_print, mock_file):
        """Test config loading with invalid JSON."""
        result = setup_headless_auth.load_config()

        assert result == {}
        mock_file.assert_called_once_with("config.json", "r")
        # Check that error message was printed (exact message may vary)
        assert mock_print.call_count == 1
        assert "❌ Error reading config.json:" in mock_print.call_args[0][0]

    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("builtins.print")
    def test_load_config_empty_json(self, mock_print, mock_file):
        """Test config loading with empty JSON."""
        result = setup_headless_auth.load_config()

        assert result == {}
        mock_file.assert_called_once_with("config.json", "r")
        mock_print.assert_not_called()


class TestSaveConfig:
    """Test cases for the save_config function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_save_config_success(self, mock_print, mock_file):
        """Test successful config saving."""
        test_config = {"test": "data", "number": 42}

        setup_headless_auth.save_config(test_config)

        mock_file.assert_called_once_with("config.json", "w")
        # Verify JSON was written
        written_data = "".join(call.args[0] for call in mock_file().write.call_args_list)
        parsed_data = json.loads(written_data)
        assert parsed_data == test_config
        mock_print.assert_called_once_with("✅ Configuration saved to config.json")

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    @patch("builtins.print")
    def test_save_config_permission_error(self, mock_print, mock_file):
        """Test config saving with permission error."""
        test_config = {"test": "data"}

        setup_headless_auth.save_config(test_config)

        mock_file.assert_called_once_with("config.json", "w")
        mock_print.assert_called_once_with("❌ Error saving config.json: Permission denied")

    @patch("builtins.open", side_effect=OSError("Disk full"))
    @patch("builtins.print")
    def test_save_config_os_error(self, mock_print, mock_file):
        """Test config saving with OS error."""
        test_config = {"test": "data"}

        setup_headless_auth.save_config(test_config)

        mock_file.assert_called_once_with("config.json", "w")
        mock_print.assert_called_once_with("❌ Error saving config.json: Disk full")


class TestSetupEmailNotifications:
    """Test cases for the setup_email_notifications function."""

    @patch("builtins.input")
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_setup_email_notifications_complete_setup(self, mock_print, mock_getpass, mock_input):
        """Test complete email notification setup."""
        # Mock user inputs
        mock_input.side_effect = [
            "sender@example.com",  # Email sender
            "receiver@example.com",  # Email receiver
            "smtp.custom.com",  # SMTP server
            "465",  # SMTP port
        ]
        mock_getpass.return_value = "app_password_123"

        config = {}
        setup_headless_auth.setup_email_notifications(config)

        # Verify config was updated
        assert config["NOTIFICATION_EMAIL_SENDER"] == "sender@example.com"
        assert config["SMTP_USERNAME"] == "sender@example.com"
        assert config["NOTIFICATION_EMAIL_RECEIVER"] == "receiver@example.com"
        assert config["SMTP_SERVER"] == "smtp.custom.com"
        assert config["SMTP_PORT"] == 465
        assert config["SMTP_PASSWORD"] == "app_password_123"

        # Verify success message was printed
        mock_print.assert_any_call("✅ App password saved")

    @patch("builtins.input")
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_setup_email_notifications_empty_inputs(self, mock_print, mock_getpass, mock_input):
        """Test email setup with empty inputs (keeping defaults)."""
        # Mock empty inputs
        mock_input.side_effect = ["", "", "", ""]
        mock_getpass.return_value = ""

        config = {
            "NOTIFICATION_EMAIL_SENDER": "existing@example.com",
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": 587,
        }

        setup_headless_auth.setup_email_notifications(config)

        # Verify config wasn't changed (empty inputs)
        assert config["NOTIFICATION_EMAIL_SENDER"] == "existing@example.com"
        assert config["SMTP_SERVER"] == "smtp.gmail.com"
        assert config["SMTP_PORT"] == 587

        # Verify warning message for empty password
        mock_print.assert_any_call("⚠️  No app password entered - you'll need to set this manually")

    @patch("builtins.input")
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_setup_email_notifications_invalid_port(self, mock_print, mock_getpass, mock_input):
        """Test email setup with invalid port number."""
        mock_input.side_effect = ["", "", "", "invalid_port"]
        mock_getpass.return_value = "password123"

        config = {"SMTP_PORT": 587}

        setup_headless_auth.setup_email_notifications(config)

        # Verify port wasn't changed due to invalid input
        assert config["SMTP_PORT"] == 587
        mock_print.assert_any_call("⚠️  Invalid port number, keeping current value")

    @patch("builtins.input")
    @patch("getpass.getpass")
    @patch("builtins.print")
    def test_setup_email_notifications_with_existing_config(
        self, mock_print, mock_getpass, mock_input
    ):
        """Test email setup with existing configuration values."""
        mock_input.side_effect = ["new_sender@example.com", "", "", ""]
        mock_getpass.return_value = "new_password"

        config = {
            "NOTIFICATION_EMAIL_SENDER": "old_sender@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "old_receiver@example.com",
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": 587,
        }

        setup_headless_auth.setup_email_notifications(config)

        # Verify only sender was updated
        assert config["NOTIFICATION_EMAIL_SENDER"] == "new_sender@example.com"
        assert config["SMTP_USERNAME"] == "new_sender@example.com"
        assert config["NOTIFICATION_EMAIL_RECEIVER"] == "old_receiver@example.com"
        assert config["SMTP_PASSWORD"] == "new_password"


class TestSetupAuthServer:
    """Test cases for the setup_auth_server function."""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_auth_server_complete_setup(self, mock_print, mock_input):
        """Test complete auth server setup."""
        mock_input.side_effect = ["0.0.0.0", "9090"]

        config = {}
        setup_headless_auth.setup_auth_server(config)

        assert config["AUTH_SERVER_HOST"] == "0.0.0.0"
        assert config["AUTH_SERVER_PORT"] == 9090

    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_auth_server_empty_inputs(self, mock_print, mock_input):
        """Test auth server setup with empty inputs."""
        mock_input.side_effect = ["", ""]

        config = {"AUTH_SERVER_HOST": "existing.host.com", "AUTH_SERVER_PORT": 8080}

        setup_headless_auth.setup_auth_server(config)

        # Config should remain unchanged
        assert config["AUTH_SERVER_HOST"] == "existing.host.com"
        assert config["AUTH_SERVER_PORT"] == 8080

    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_auth_server_invalid_port(self, mock_print, mock_input):
        """Test auth server setup with invalid port."""
        mock_input.side_effect = ["localhost", "not_a_number"]

        config = {"AUTH_SERVER_PORT": 8080}

        setup_headless_auth.setup_auth_server(config)

        assert config["AUTH_SERVER_HOST"] == "localhost"
        assert config["AUTH_SERVER_PORT"] == 8080  # Should remain unchanged
        mock_print.assert_any_call("⚠️  Invalid port number, keeping current value")

    @patch("builtins.input")
    @patch("builtins.print")
    def test_setup_auth_server_defaults_displayed(self, mock_print, mock_input):
        """Test that default values are displayed correctly."""
        mock_input.side_effect = ["", ""]

        config = {}
        setup_headless_auth.setup_auth_server(config)

        # Verify default values were displayed
        mock_print.assert_any_call("Current host: localhost")
        mock_print.assert_any_call("Current port: 8080")


class TestCheckCredentialsFile:
    """Test cases for the check_credentials_file function."""

    @patch("os.path.exists", return_value=True)
    @patch("builtins.print")
    def test_check_credentials_file_exists(self, mock_print, mock_exists):
        """Test when credentials file exists."""
        result = setup_headless_auth.check_credentials_file()

        assert result is True
        mock_exists.assert_called_once_with("credentials.json")
        mock_print.assert_any_call("✅ Found credentials.json")

    @patch("os.path.exists", return_value=False)
    @patch("builtins.print")
    def test_check_credentials_file_missing(self, mock_print, mock_exists):
        """Test when credentials file is missing."""
        result = setup_headless_auth.check_credentials_file()

        assert result is False
        mock_exists.assert_called_once_with("credentials.json")
        mock_print.assert_any_call("❌ credentials.json not found!")
        # Verify setup instructions were printed
        mock_print.assert_any_call("1. Go to https://console.cloud.google.com/")
        mock_print.assert_any_call("4. Create OAuth 2.0 credentials (Desktop application)")


class TestTestConfiguration:
    """Test cases for the test_configuration function."""

    @patch("builtins.print")
    def test_test_configuration_success(self, mock_print):
        """Test successful configuration testing."""
        # Mock HeadlessAuthManager and its methods
        mock_auth_manager = MagicMock()
        mock_token_status = {
            "valid": True,
            "expired": False,
            "needs_refresh": False,
            "expiry": "2024-12-31T23:59:59Z",
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        with patch("headless_auth.HeadlessAuthManager", return_value=mock_auth_manager):
            setup_headless_auth.test_configuration()

        # Verify status was printed
        mock_print.assert_any_call("Token valid: True")
        mock_print.assert_any_call("Token expired: False")
        mock_print.assert_any_call("Token expiry: 2024-12-31T23:59:59Z")
        mock_print.assert_any_call("✅ Token is valid!")

    @patch("builtins.print")
    def test_test_configuration_invalid_token(self, mock_print):
        """Test configuration testing with invalid token."""
        mock_auth_manager = MagicMock()
        mock_token_status = {"valid": False, "expired": True, "needs_refresh": True}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        with patch("headless_auth.HeadlessAuthManager", return_value=mock_auth_manager):
            setup_headless_auth.test_configuration()

        # Verify warning messages were printed
        mock_print.assert_any_call("Token valid: False")
        mock_print.assert_any_call("\n⚠️  No valid token found - you'll need to authenticate")
        mock_print.assert_any_call(
            "Run the application with --headless flag to start authentication"
        )

    @patch("builtins.print")
    def test_test_configuration_import_error(self, mock_print):
        """Test configuration testing when headless_auth import fails."""
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'headless_auth'")
        ):
            setup_headless_auth.test_configuration()

        mock_print.assert_any_call(
            "❌ Error importing headless auth modules: No module named 'headless_auth'"
        )

    @patch("builtins.print")
    def test_test_configuration_general_exception(self, mock_print):
        """Test configuration testing with general exception."""
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_token_status.side_effect = Exception("Connection failed")

        with patch("headless_auth.HeadlessAuthManager", return_value=mock_auth_manager):
            setup_headless_auth.test_configuration()

        mock_print.assert_any_call("❌ Error testing configuration: Connection failed")

    @patch("builtins.print")
    def test_test_configuration_no_expiry(self, mock_print):
        """Test configuration testing when token has no expiry."""
        mock_auth_manager = MagicMock()
        mock_token_status = {
            "valid": True,
            "expired": False,
            "needs_refresh": False,
            # No expiry field
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        with patch("headless_auth.HeadlessAuthManager", return_value=mock_auth_manager):
            setup_headless_auth.test_configuration()

        # Should not print expiry line
        mock_print.assert_any_call("Token valid: True")
        # Verify expiry line was not called
        expiry_calls = [call for call in mock_print.call_args_list if "Token expiry:" in str(call)]
        assert len(expiry_calls) == 0


class TestMainFunction:
    """Test cases for the main function."""

    @patch("setup_headless_auth.test_configuration")
    @patch("setup_headless_auth.save_config")
    @patch("setup_headless_auth.setup_auth_server")
    @patch("setup_headless_auth.setup_email_notifications")
    @patch("setup_headless_auth.check_credentials_file")
    @patch("setup_headless_auth.load_config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_main_complete_setup_with_credentials(
        self,
        mock_print,
        mock_input,
        mock_load_config,
        mock_check_creds,
        mock_setup_email,
        mock_setup_auth,
        mock_save_config,
        mock_test_config,
    ):
        """Test complete main function execution with credentials present."""
        # Setup mocks
        mock_load_config.return_value = {"existing": "config"}
        mock_check_creds.return_value = True
        mock_input.side_effect = ["y", "yes", "Y"]  # Setup email, auth server, test config

        result = setup_headless_auth.main()

        # Verify return value
        assert result == 0

        # Verify function calls
        mock_load_config.assert_called_once()
        mock_check_creds.assert_called_once()
        mock_setup_email.assert_called_once_with({"existing": "config"})
        mock_setup_auth.assert_called_once_with({"existing": "config"})
        mock_save_config.assert_called_once_with({"existing": "config"})
        mock_test_config.assert_called_once()

        # Verify success messages
        mock_print.assert_any_call("✅ Ready for headless authentication")
        mock_print.assert_any_call("1. Run your application with --headless flag")

    @patch("setup_headless_auth.test_configuration")
    @patch("setup_headless_auth.save_config")
    @patch("setup_headless_auth.setup_auth_server")
    @patch("setup_headless_auth.setup_email_notifications")
    @patch("setup_headless_auth.check_credentials_file")
    @patch("setup_headless_auth.load_config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_main_no_credentials(
        self,
        mock_print,
        mock_input,
        mock_load_config,
        mock_check_creds,
        mock_setup_email,
        mock_setup_auth,
        mock_save_config,
        mock_test_config,
    ):
        """Test main function when credentials file is missing."""
        mock_load_config.return_value = {"test": "config"}
        mock_check_creds.return_value = False
        mock_input.side_effect = ["n", "n", "n"]  # Skip all optional setups

        result = setup_headless_auth.main()

        assert result == 0

        # Verify warning messages for missing credentials
        mock_print.assert_any_call("⚠️  Please add Google credentials file first")
        mock_print.assert_any_call("Then re-run this setup script")

    @patch("setup_headless_auth.load_config")
    @patch("builtins.print")
    def test_main_config_load_failure(self, mock_print, mock_load_config):
        """Test main function when config loading fails."""
        mock_load_config.return_value = {}  # Empty config indicates failure

        result = setup_headless_auth.main()

        assert result == 1
        mock_print.assert_any_call("❌ Could not load configuration. Please check config.json")

    @patch("setup_headless_auth.test_configuration")
    @patch("setup_headless_auth.save_config")
    @patch("setup_headless_auth.check_credentials_file")
    @patch("setup_headless_auth.load_config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_main_skip_all_optional_setups(
        self,
        mock_print,
        mock_input,
        mock_load_config,
        mock_check_creds,
        mock_save_config,
        mock_test_config,
    ):
        """Test main function skipping all optional setups."""
        mock_load_config.return_value = {"test": "config"}
        mock_check_creds.return_value = True
        mock_input.side_effect = ["N", "N", "n"]  # Skip email, auth server, and test config

        result = setup_headless_auth.main()

        assert result == 0

        # Verify save_config was still called
        mock_save_config.assert_called_once()
        # Verify test_configuration was NOT called
        mock_test_config.assert_not_called()

    @patch("setup_headless_auth.test_configuration")
    @patch("setup_headless_auth.save_config")
    @patch("setup_headless_auth.setup_auth_server")
    @patch("setup_headless_auth.setup_email_notifications")
    @patch("setup_headless_auth.check_credentials_file")
    @patch("setup_headless_auth.load_config")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_main_case_insensitive_inputs(
        self,
        mock_print,
        mock_input,
        mock_load_config,
        mock_check_creds,
        mock_setup_email,
        mock_setup_auth,
        mock_save_config,
        mock_test_config,
    ):
        """Test main function with various case inputs."""
        mock_load_config.return_value = {"test": "config"}
        mock_check_creds.return_value = True
        mock_input.side_effect = ["YES", "y", "NO"]  # Mixed case inputs

        result = setup_headless_auth.main()

        assert result == 0

        # Verify both email and auth server setup were called
        mock_setup_email.assert_called_once()
        mock_setup_auth.assert_called_once()
        # Verify test config was NOT called (NO input)
        mock_test_config.assert_not_called()


class TestScriptExecution:
    """Test cases for script execution."""

    @patch("setup_headless_auth.main")
    @patch("sys.exit")
    def test_script_execution(self, mock_exit, mock_main):
        """Test script execution when run as main."""
        mock_main.return_value = 0

        # Test the script execution logic directly
        sys.exit(setup_headless_auth.main())

        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("setup_headless_auth.main")
    @patch("sys.exit")
    def test_script_execution_with_error(self, mock_exit, mock_main):
        """Test script execution when main returns error code."""
        mock_main.return_value = 1

        sys.exit(setup_headless_auth.main())

        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(1)
