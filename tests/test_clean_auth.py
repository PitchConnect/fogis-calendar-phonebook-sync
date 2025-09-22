"""Tests for clean_auth module."""

import json
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

import clean_auth


class TestCleanAuthMain:
    """Test cases for the main function in clean_auth."""

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_success(self, mock_print, mock_file_open, mock_input, mock_flow_class):
        """Test successful authentication flow."""
        # Mock config file content
        mock_config = {
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
            ]
        }

        # Mock file operations
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file_open.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test_code&state=test_state"

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test_token"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow_instance

        # Execute main function
        result = clean_auth.main()

        # Verify success
        assert result == 0

        # Verify flow was created correctly with redirect URI
        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            "credentials.json",
            mock_config["SCOPES"],
            redirect_uri="http://localhost:8080/callback",
        )

        # Verify authorization URL was generated
        mock_flow_instance.authorization_url.assert_called_once_with(
            access_type="offline", prompt="consent", include_granted_scopes="true"
        )

        # Verify token exchange was called
        mock_flow_instance.fetch_token.assert_called_once_with(
            authorization_response="http://localhost:8080/callback?code=test_code&state=test_state"
        )

        # Verify token was saved
        token_file.return_value.write.assert_called_once_with('{"token": "test_token"}')

        # Verify success messages were printed
        mock_print.assert_any_call("✅ Authentication successful!")
        mock_print.assert_any_call("✅ Token saved to token.json")

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_success_with_default_scopes(
        self, mock_print, mock_file_open, mock_input, mock_flow_class
    ):
        """Test successful authentication with default scopes when config has no SCOPES."""
        # Mock config file content without SCOPES
        mock_config = {"OTHER_CONFIG": "value"}

        # Mock file operations
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file_open.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test_code&state=test_state"

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test_token"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow_instance

        # Execute main function
        result = clean_auth.main()

        # Verify success
        assert result == 0

        # Verify flow was created with default scopes
        expected_default_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/drive",
        ]
        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            "credentials.json",
            expected_default_scopes,
            redirect_uri="http://localhost:8080/callback",
        )

    @patch("builtins.print")
    def test_main_import_error(self, mock_print):
        """Test main function when google_auth_oauthlib is not available."""
        # Mock ImportError by patching the import at the module level
        import sys

        original_modules = sys.modules.copy()

        # Remove the module if it exists to force ImportError
        if "google_auth_oauthlib.flow" in sys.modules:
            del sys.modules["google_auth_oauthlib.flow"]
        if "google_auth_oauthlib" in sys.modules:
            del sys.modules["google_auth_oauthlib"]

        # Mock the import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == "google_auth_oauthlib.flow":
                raise ImportError("No module named 'google_auth_oauthlib'")
            return original_modules.get(name)

        with patch("builtins.__import__", side_effect=mock_import):
            result = clean_auth.main()

            # Verify error return code
            assert result == 1

            # Verify error messages were printed
            mock_print.assert_any_call(
                "❌ Missing required library: No module named 'google_auth_oauthlib'"
            )
            mock_print.assert_any_call("💡 Try: pip install google-auth-oauthlib")

        # Restore original modules
        sys.modules.update(original_modules)

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_config_file_not_found(self, mock_print, mock_file_open, mock_flow_class):
        """Test main function when config.json is not found."""
        # Mock FileNotFoundError when opening config.json
        mock_file_open.side_effect = FileNotFoundError("config.json not found")

        result = clean_auth.main()

        # Verify error return code
        assert result == 1

        # Verify error messages were printed
        mock_print.assert_any_call("❌ File not found: config.json not found")
        mock_print.assert_any_call("💡 Make sure credentials.json and config.json exist")

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_credentials_file_not_found(self, mock_print, mock_file_open, mock_flow_class):
        """Test main function when credentials.json is not found."""
        # Mock config file content
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file_open.return_value = config_file.return_value

        # Mock FileNotFoundError when creating flow
        mock_flow_class.from_client_secrets_file.side_effect = FileNotFoundError(
            "credentials.json not found"
        )

        result = clean_auth.main()

        # Verify error return code
        assert result == 1

        # Verify error messages were printed
        mock_print.assert_any_call("❌ File not found: credentials.json not found")
        mock_print.assert_any_call("💡 Make sure credentials.json and config.json exist")

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_authentication_failure(
        self, mock_print, mock_file_open, mock_input, mock_flow_class
    ):
        """Test main function when authentication fails."""
        # Mock config file content
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file_open.return_value = config_file.return_value

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test_code&state=test_state"

        # Mock flow that raises exception during authentication
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.fetch_token.side_effect = Exception("Authentication failed")
        mock_flow_class.from_client_secrets_file.return_value = mock_flow_instance

        result = clean_auth.main()

        # Verify error return code
        assert result == 1

        # Verify error messages were printed
        mock_print.assert_any_call("❌ Authentication failed: Authentication failed")
        mock_print.assert_any_call("💡 Check your internet connection and try again")

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_token_save_failure(self, mock_print, mock_file_open, mock_input, mock_flow_class):
        """Test main function when token saving fails."""
        # Mock config file content
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}

        # Mock file operations - config succeeds, token save fails
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        token_file.return_value.write.side_effect = Exception("Permission denied")
        mock_file_open.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test_code&state=test_state"

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.to_json.return_value = '{"token": "test_token"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow_instance

        result = clean_auth.main()

        # Verify error return code
        assert result == 1

        # Verify error messages were printed
        mock_print.assert_any_call("❌ Authentication failed: Permission denied")
        mock_print.assert_any_call("💡 Check your internet connection and try again")

    @patch("google_auth_oauthlib.flow.Flow")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("builtins.print")
    def test_main_credentials_without_refresh_token(
        self, mock_print, mock_file_open, mock_input, mock_flow_class
    ):
        """Test main function when credentials don't have refresh token."""
        # Mock config file content
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}

        # Mock file operations
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file_open.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test_code&state=test_state"

        # Mock credentials without refresh token
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = None  # No refresh token
        mock_credentials.to_json.return_value = '{"token": "test_token"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow_instance

        # Execute main function
        result = clean_auth.main()

        # Verify success
        assert result == 0

        # Verify refresh token status was printed correctly
        mock_print.assert_any_call("✅ Has refresh token: False")


class TestCleanAuthScriptExecution:
    """Test cases for script execution."""

    @patch("clean_auth.main")
    @patch("sys.exit")
    def test_script_execution(self, mock_exit, mock_main):
        """Test script execution when run as main."""
        mock_main.return_value = 0

        # Test the script execution logic directly
        # This simulates what happens in the if __name__ == "__main__" block
        sys.exit(clean_auth.main())

        # Verify main was called and exit was called with return value
        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)


class TestEnvironmentVariable:
    """Test cases for environment variable setting."""

    def test_oauthlib_insecure_transport_set(self):
        """Test that OAUTHLIB_INSECURE_TRANSPORT is set correctly."""
        # Import the module to trigger the environment variable setting
        import os

        import clean_auth

        # Verify the environment variable is set
        assert os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") == "1"
