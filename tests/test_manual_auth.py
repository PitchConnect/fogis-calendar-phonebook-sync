"""Tests for manual_auth module."""

import json
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

import manual_auth


class TestMainFunction:
    """Test cases for the main function in manual_auth."""

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_success_with_default_scopes(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test successful authentication flow with default scopes."""
        # Mock config file content without SCOPES (should use defaults)
        mock_config = {"OTHER_CONFIG": "value"}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input
        mock_input.return_value = (
            "http://localhost:8080/callback?code=test_code&state=test_state"
        )

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test_token"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state123",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        result = manual_auth.main()

        # Verify return value
        assert result == 0

        # Verify flow was created with default scopes and redirect URI
        expected_default_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/drive",
        ]
        mock_flow_from_file.assert_called_once_with(
            "credentials.json",
            expected_default_scopes,
            redirect_uri="http://localhost:8080/callback",
        )

        # Verify auth URL was generated
        mock_flow_instance.authorization_url.assert_called_once_with(
            access_type="offline", prompt="consent"
        )

        # Verify token fetch was called
        mock_flow_instance.fetch_token.assert_called_once_with(
            authorization_response="http://localhost:8080/callback?code=test_code&state=test_state"
        )

        # Verify token was saved
        token_file.return_value.write.assert_called_once_with('{"token": "test_token"}')

        # Verify success messages were printed
        mock_print.assert_any_call("✅ Authentication successful!")
        mock_print.assert_any_call("✅ Token saved to token.json")
        mock_print.assert_any_call("✅ Token expires: 2024-12-31T23:59:59Z")
        mock_print.assert_any_call("✅ Has refresh token: True")

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_success_with_custom_scopes(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test successful authentication flow with custom scopes from config."""
        # Mock config file content with custom SCOPES
        mock_config = {
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts.readonly",
            ]
        }
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input
        mock_input.return_value = "http://localhost:8080/callback?code=custom_code"

        # Mock credentials without refresh token
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-06-15T12:00:00Z"
        mock_credentials.refresh_token = None
        mock_credentials.to_json.return_value = '{"access_token": "access_123"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://custom.auth.url",
            "custom_state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        result = manual_auth.main()

        # Verify return value
        assert result == 0

        # Verify flow was created with custom scopes and redirect URI
        expected_custom_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts.readonly",
        ]
        mock_flow_from_file.assert_called_once_with(
            "credentials.json",
            expected_custom_scopes,
            redirect_uri="http://localhost:8080/callback",
        )

        # Verify custom scopes were printed
        mock_print.assert_any_call("  - https://www.googleapis.com/auth/calendar")
        mock_print.assert_any_call(
            "  - https://www.googleapis.com/auth/contacts.readonly"
        )

        # Verify refresh token status (False for None)
        mock_print.assert_any_call("✅ Has refresh token: False")

    @patch("builtins.open", side_effect=FileNotFoundError("config.json not found"))
    @patch("builtins.print")
    def test_main_config_file_not_found(self, mock_print, mock_file):
        """Test main function when config.json is not found."""
        # The config loading is not in a try-catch, so exception should be raised
        with pytest.raises(FileNotFoundError, match="config.json not found"):
            manual_auth.main()

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": json}')
    @patch("builtins.print")
    def test_main_invalid_json_config(self, mock_print, mock_file):
        """Test main function when config.json contains invalid JSON."""
        # JSON parsing is not in a try-catch, so exception should be raised
        with pytest.raises(json.JSONDecodeError):
            manual_auth.main()

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_credentials_file_not_found(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test main function when credentials.json is not found."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock flow creation failure - this is not in a try-catch, so exception should be raised
        mock_flow_from_file.side_effect = FileNotFoundError(
            "credentials.json not found"
        )

        with pytest.raises(FileNotFoundError, match="credentials.json not found"):
            manual_auth.main()

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_authorization_url_failure(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test main function when authorization URL generation fails."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock flow that fails during authorization_url - this is not in a try-catch, so exception should be raised
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.side_effect = Exception(
            "Auth URL generation failed"
        )
        mock_flow_from_file.return_value = mock_flow_instance

        with pytest.raises(Exception, match="Auth URL generation failed"):
            manual_auth.main()

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_fetch_token_failure(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test main function when token fetching fails."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock user input
        mock_input.return_value = "invalid_callback_url"

        # Mock flow that fails during fetch_token
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.fetch_token.side_effect = Exception(
            "Invalid authorization response"
        )
        mock_flow_from_file.return_value = mock_flow_instance

        result = manual_auth.main()

        # Should return error code
        assert result == 1

        # Verify error was printed
        mock_print.assert_any_call("❌ Error: Invalid authorization response")

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_token_save_failure(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test main function when token saving fails."""
        # Mock config file (first call) and token file write failure (second call)
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        token_file.return_value.write.side_effect = PermissionError("Permission denied")
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock user input
        mock_input.return_value = "http://localhost:8080/callback?code=test"

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://auth.url",
            "state",
        )
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        result = manual_auth.main()

        # Should return error code
        assert result == 1

        # Verify error was printed
        mock_print.assert_any_call("❌ Error: Permission denied")

    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file")
    @patch("builtins.print")
    def test_main_instructions_printed(
        self, mock_print, mock_flow_from_file, mock_file, mock_input
    ):
        """Test that user instructions are properly printed."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock user input
        mock_input.return_value = "http://localhost:8080/callback?code=test"

        # Mock flow that fails to avoid full execution
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://example.auth.url",
            "state",
        )
        mock_flow_instance.fetch_token.side_effect = Exception("Stop execution")
        mock_flow_from_file.return_value = mock_flow_instance

        manual_auth.main()

        # Verify instructions were printed
        mock_print.assert_any_call("🔐 Manual Authentication for All Google Services")
        mock_print.assert_any_call("=" * 50)
        mock_print.assert_any_call("Required scopes:")
        mock_print.assert_any_call("🔗 Authentication URL:")
        mock_print.assert_any_call("https://example.auth.url")
        mock_print.assert_any_call("📋 Instructions:")
        mock_print.assert_any_call("1. Copy the URL above and paste it in your browser")
        mock_print.assert_any_call("2. Complete Google authentication")
        mock_print.assert_any_call("3. Copy the FULL callback URL from your browser")
        mock_print.assert_any_call("4. Paste it below when prompted")


class TestScriptExecution:
    """Test cases for script execution."""

    @patch("manual_auth.main")
    def test_script_execution_success(self, mock_main):
        """Test script execution when main returns success."""
        mock_main.return_value = 0

        # Test the script execution logic directly
        with patch("builtins.exit") as mock_exit:
            exec("exit(manual_auth.main())")

        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("manual_auth.main")
    def test_script_execution_error(self, mock_main):
        """Test script execution when main returns error code."""
        mock_main.return_value = 1

        # Test the script execution logic directly
        with patch("builtins.exit") as mock_exit:
            exec("exit(manual_auth.main())")

        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(1)
