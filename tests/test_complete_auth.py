"""Tests for complete_auth module."""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

import complete_auth


class TestCompleteAuthScript:
    """Test cases for the complete_auth script."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_success_with_default_scopes(
        self, mock_print, mock_flow_from_file, mock_file
    ):
        """Test successful authentication completion with default scopes."""
        # Mock config file content without SCOPES (should use defaults)
        mock_config = {"OTHER_CONFIG": "value"}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials with refresh token
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = (
            '{"token": "test_token", "refresh_token": "refresh_token_123"}'
        )

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script by importing it (this runs the main code)
        import importlib

        importlib.reload(complete_auth)

        # Verify flow was created with default scopes
        expected_default_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
        ]
        mock_flow_from_file.assert_called_once_with("credentials.json", expected_default_scopes)

        # Verify redirect URI was set
        assert mock_flow_instance.redirect_uri == "http://localhost:8080/callback"

        # Verify token fetch was called with hardcoded authorization response
        expected_auth_response = "http://localhost:8080/callback?state=CdJuw0chqZcjvJuuXkWBpi5stuRbIt&code=4/0AUJR-x5MEnNaC-qrNTtXNccEiNgW88oyFXgehj4T8Ba8Vah14kewUQiK_stP6XaX9ZE4mQ&scope=https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/calendar"
        mock_flow_instance.fetch_token.assert_called_once_with(
            authorization_response=expected_auth_response
        )

        # Verify token was saved
        token_file.return_value.write.assert_called_once_with(
            '{"token": "test_token", "refresh_token": "refresh_token_123"}'
        )

        # Verify success messages were printed
        mock_print.assert_any_call("✅ Authentication successful!")
        mock_print.assert_any_call("✅ Token saved to token.json")
        mock_print.assert_any_call("✅ Token expires: 2024-12-31T23:59:59Z")
        mock_print.assert_any_call("✅ Has refresh token: True")

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_success_with_custom_scopes(
        self, mock_print, mock_flow_from_file, mock_file
    ):
        """Test successful authentication completion with custom scopes from config."""
        # Mock config file content with custom SCOPES
        mock_config = {
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts.readonly",
                "https://www.googleapis.com/auth/drive",
            ]
        }
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials without refresh token
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-06-15T12:00:00Z"
        mock_credentials.refresh_token = None
        mock_credentials.to_json.return_value = '{"access_token": "access_123"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify flow was created with custom scopes
        expected_custom_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts.readonly",
            "https://www.googleapis.com/auth/drive",
        ]
        mock_flow_from_file.assert_called_once_with("credentials.json", expected_custom_scopes)

        # Verify refresh token status (False for None)
        mock_print.assert_any_call("✅ Has refresh token: False")

    @patch("builtins.open", side_effect=FileNotFoundError("config.json not found"))
    @patch("builtins.print")
    def test_complete_auth_config_file_not_found(self, mock_print, mock_file):
        """Test complete_auth script when config.json is not found."""
        # The config loading is not in a try-catch, so exception should be raised
        with pytest.raises(FileNotFoundError, match="config.json not found"):
            import importlib

            importlib.reload(complete_auth)

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": json}')
    @patch("builtins.print")
    def test_complete_auth_invalid_json_config(self, mock_print, mock_file):
        """Test complete_auth script when config.json contains invalid JSON."""
        # JSON parsing is not in a try-catch, so exception should be raised
        with pytest.raises(json.JSONDecodeError):
            import importlib

            importlib.reload(complete_auth)

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_credentials_file_not_found(
        self, mock_print, mock_flow_from_file, mock_file
    ):
        """Test complete_auth script when credentials.json is not found."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock flow creation failure - this is not in a try-catch, so exception should be raised
        mock_flow_from_file.side_effect = FileNotFoundError("credentials.json not found")

        with pytest.raises(FileNotFoundError, match="credentials.json not found"):
            import importlib

            importlib.reload(complete_auth)

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    @patch("traceback.print_exc")
    def test_complete_auth_fetch_token_failure(
        self, mock_traceback, mock_print, mock_flow_from_file, mock_file
    ):
        """Test complete_auth script when token fetching fails."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        mock_file.return_value = config_file.return_value

        # Mock flow that fails during fetch_token
        mock_flow_instance = MagicMock()
        mock_flow_instance.fetch_token.side_effect = Exception("Invalid authorization response")
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify error was printed
        mock_print.assert_any_call("❌ Error: Invalid authorization response")
        # Verify traceback was printed
        mock_traceback.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    @patch("traceback.print_exc")
    def test_complete_auth_token_save_failure(
        self, mock_traceback, mock_print, mock_flow_from_file, mock_file
    ):
        """Test complete_auth script when token saving fails."""
        # Mock config file (first call) and token file write failure (second call)
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        token_file.return_value.write.side_effect = PermissionError("Permission denied")
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify error was printed
        mock_print.assert_any_call("❌ Error: Permission denied")
        # Verify traceback was printed
        mock_traceback.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_credentials_without_expiry(
        self, mock_print, mock_flow_from_file, mock_file
    ):
        """Test complete_auth script when credentials have no expiry."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials without expiry
        mock_credentials = MagicMock()
        mock_credentials.expiry = None
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify expiry was printed as None
        mock_print.assert_any_call("✅ Token expires: None")
        mock_print.assert_any_call("✅ Has refresh token: True")

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_hardcoded_authorization_response(
        self, mock_print, mock_flow_from_file, mock_file
    ):
        """Test that the script uses the correct hardcoded authorization response."""
        # Mock config file
        mock_config = {"SCOPES": ["https://www.googleapis.com/auth/calendar"]}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify the exact hardcoded authorization response was used
        expected_auth_response = "http://localhost:8080/callback?state=CdJuw0chqZcjvJuuXkWBpi5stuRbIt&code=4/0AUJR-x5MEnNaC-qrNTtXNccEiNgW88oyFXgehj4T8Ba8Vah14kewUQiK_stP6XaX9ZE4mQ&scope=https://www.googleapis.com/auth/contacts%20https://www.googleapis.com/auth/calendar"
        mock_flow_instance.fetch_token.assert_called_once_with(
            authorization_response=expected_auth_response
        )

        # Verify redirect URI was set correctly
        assert mock_flow_instance.redirect_uri == "http://localhost:8080/callback"


class TestCompleteAuthEdgeCases:
    """Test edge cases and boundary conditions for complete_auth script."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_empty_config(self, mock_print, mock_flow_from_file, mock_file):
        """Test complete_auth script with empty config file."""
        # Mock empty config file
        config_file = mock_open(read_data="{}")
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify flow was created with default scopes (empty config should use defaults)
        expected_default_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
        ]
        mock_flow_from_file.assert_called_once_with("credentials.json", expected_default_scopes)

    @patch("builtins.open", new_callable=mock_open)
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.print")
    def test_complete_auth_empty_scopes_list(self, mock_print, mock_flow_from_file, mock_file):
        """Test complete_auth script with empty SCOPES list in config."""
        # Mock config with empty SCOPES list
        mock_config = {"SCOPES": []}
        config_file = mock_open(read_data=json.dumps(mock_config))
        token_file = mock_open()
        mock_file.side_effect = [config_file.return_value, token_file.return_value]

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.expiry = "2024-12-31T23:59:59Z"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.to_json.return_value = '{"token": "test"}'

        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_from_file.return_value = mock_flow_instance

        # Execute the script
        import importlib

        importlib.reload(complete_auth)

        # Verify flow was created with empty scopes list (as specified in config)
        mock_flow_from_file.assert_called_once_with("credentials.json", [])
