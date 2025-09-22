"""Tests for the token_manager module."""

import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest
from google.oauth2.credentials import Credentials

import token_manager


@pytest.fixture
def mock_config():
    """Return a mock configuration for testing."""
    return {
        "SCOPES": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
        ],
        "TOKEN_REFRESH_BUFFER_DAYS": 6,
        "AUTH_SERVER_HOST": "localhost",
        "AUTH_SERVER_PORT": 8080,
    }


@pytest.fixture
def mock_credentials():
    """Return mock credentials for testing."""
    mock_creds = MagicMock(spec=Credentials)
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.refresh_token = "refresh_token"
    mock_creds.expiry = datetime.datetime.now() + datetime.timedelta(days=30)
    mock_creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    mock_creds.to_json.return_value = '{"token": "test_token"}'
    return mock_creds


@pytest.fixture
def mock_expired_credentials():
    """Return mock expired credentials for testing."""
    mock_creds = MagicMock(spec=Credentials)
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token"
    mock_creds.expiry = datetime.datetime.now() - datetime.timedelta(days=1)
    mock_creds.scopes = ["https://www.googleapis.com/auth/calendar"]
    return mock_creds


class TestTokenManagerClass:
    """Test cases for the TokenManager class."""

    @pytest.mark.unit
    def test_init(self, mock_config):
        """Test TokenManager initialization."""
        tm = token_manager.TokenManager(mock_config)

        assert tm.config == mock_config
        assert tm.credentials_file == "credentials.json"
        assert tm.token_file == "token.json"
        assert tm.scopes == mock_config["SCOPES"]
        assert tm.refresh_buffer_days == 6
        assert tm._credentials is None

    @pytest.mark.unit
    def test_get_credentials_valid_file(self, mock_config, mock_credentials):
        """Test getting credentials from valid token file."""
        tm = token_manager.TokenManager(mock_config)

        with patch("os.path.exists", return_value=True), patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_credentials,
        ):

            result = tm.get_credentials()
            assert result == mock_credentials
            assert tm._credentials == mock_credentials

    @pytest.mark.unit
    def test_get_credentials_no_token_file(self, mock_config):
        """Test getting credentials when no token file exists."""
        tm = token_manager.TokenManager(mock_config)

        with patch("os.path.exists", return_value=False):
            result = tm.get_credentials()
            assert result is None

    @pytest.mark.unit
    def test_get_credentials_invalid_format(self, mock_config):
        """Test getting credentials from invalid token file."""
        tm = token_manager.TokenManager(mock_config)

        with patch("os.path.exists", return_value=True), patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            side_effect=Exception("Invalid format"),
        ):

            result = tm.get_credentials()
            assert result is None

    @pytest.mark.unit
    def test_check_token_expiration_no_token(self, mock_config):
        """Test checking token expiration when no token exists."""
        tm = token_manager.TokenManager(mock_config)

        with patch.object(tm, "get_credentials", return_value=None):
            needs_refresh, expiry = tm.check_token_expiration()
            assert needs_refresh is True
            assert expiry is None

    @pytest.mark.unit
    def test_check_token_expiration_valid(self, mock_config, mock_credentials):
        """Test checking token expiration for valid token."""
        tm = token_manager.TokenManager(mock_config)

        # Set expiry to 30 days from now (well beyond buffer)
        mock_credentials.expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)

        with patch.object(tm, "get_credentials", return_value=mock_credentials):
            needs_refresh, expiry = tm.check_token_expiration()
            assert needs_refresh is False
            assert expiry == mock_credentials.expiry

    @pytest.mark.unit
    def test_check_token_expiration_near_expiry(self, mock_config, mock_credentials):
        """Test checking token expiration for token near expiry."""
        tm = token_manager.TokenManager(mock_config)

        # Set expiry to 3 days from now (within 6-day buffer)
        mock_credentials.expiry = datetime.datetime.utcnow() + datetime.timedelta(days=3)

        with patch.object(tm, "get_credentials", return_value=mock_credentials):
            needs_refresh, expiry = tm.check_token_expiration()
            assert needs_refresh is True
            assert expiry == mock_credentials.expiry

    @pytest.mark.unit
    def test_initiate_auth_flow(self, mock_config):
        """Test initiating OAuth flow."""
        tm = token_manager.TokenManager(mock_config)

        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state123")

        with patch("os.path.exists", return_value=True), patch(
            "google_auth_oauthlib.flow.Flow.from_client_secrets_file",
            return_value=mock_flow,
        ):
            auth_url = tm.initiate_auth_flow()

            assert auth_url == "http://auth.url"
            assert hasattr(tm, "_flow")
            assert tm._flow == mock_flow

    @pytest.mark.unit
    def test_complete_auth_flow_success(self, mock_config, mock_credentials):
        """Test completing OAuth flow successfully."""
        tm = token_manager.TokenManager(mock_config)

        # Set up mock flow
        mock_flow = MagicMock()
        mock_flow.credentials = mock_credentials
        tm._flow = mock_flow

        with patch.object(tm, "_save_token", return_value=True):
            result = tm.complete_auth_flow("http://callback.url?code=auth_code")

            assert result is True
            assert tm._credentials == mock_credentials
            mock_flow.fetch_token.assert_called_once()

    @pytest.mark.unit
    def test_complete_auth_flow_no_flow(self, mock_config):
        """Test completing OAuth flow without active flow."""
        tm = token_manager.TokenManager(mock_config)

        result = tm.complete_auth_flow("http://callback.url?code=auth_code")
        assert result is False

    @pytest.mark.unit
    def test_get_token_info_valid_token(self, mock_config, mock_credentials):
        """Test getting token info for valid token."""
        tm = token_manager.TokenManager(mock_config)

        with patch.object(tm, "get_credentials", return_value=mock_credentials), patch.object(
            tm, "check_token_expiration", return_value=(False, mock_credentials.expiry)
        ):

            info = tm.get_token_info()

            assert info["valid"] is True
            assert info["expired"] is False
            assert info["needs_refresh"] is False
            assert info["has_refresh_token"] is True
            assert info["expiry"] is not None

    @pytest.mark.unit
    def test_get_token_info_no_token(self, mock_config):
        """Test getting token info when no token exists."""
        tm = token_manager.TokenManager(mock_config)

        with patch.object(tm, "get_credentials", return_value=None):
            info = tm.get_token_info()

            assert info["valid"] is False
            assert info["expired"] is True
            assert info["needs_refresh"] is True
            assert info["expiry"] is None


class TestTokenManagerFunctions:
    """Test cases for token_manager module functions that exist."""

    @pytest.mark.unit
    def test_token_manager_class_functionality(self, mock_config):
        """Test TokenManager class functionality comprehensively."""
        tm = token_manager.TokenManager(mock_config)

        # Test initialization
        assert tm.config == mock_config
        assert tm.scopes == mock_config["SCOPES"]

        # Test token info when no token exists
        with patch.object(tm, "get_credentials", return_value=None):
            info = tm.get_token_info()
            assert info["valid"] is False
            assert info["expired"] is True
            assert info["needs_refresh"] is True

    @pytest.mark.unit
    def test_token_manager_save_functionality(self, mock_config):
        """Test TokenManager save functionality."""
        tm = token_manager.TokenManager(mock_config)

        with patch("builtins.open", mock_open()) as mock_file:
            tm._save_token()
            # Should attempt to save token
            mock_file.assert_called_once()

    @pytest.mark.unit
    def test_token_manager_error_handling(self, mock_config):
        """Test TokenManager error handling."""
        tm = token_manager.TokenManager(mock_config)

        # Test with invalid credentials file
        with patch("os.path.exists", return_value=True), patch(
            "google_auth_oauthlib.flow.Flow.from_client_secrets_file",
            side_effect=Exception("Invalid credentials"),
        ):
            try:
                tm.initiate_auth_flow()
            except Exception:
                # Should handle the error gracefully
                pass

    @pytest.mark.unit
    def test_token_manager_refresh_logic(self, mock_config, mock_credentials):
        """Test TokenManager refresh logic."""
        tm = token_manager.TokenManager(mock_config)

        # Test with credentials that need refresh
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"

        with patch.object(tm, "get_credentials", return_value=mock_credentials), patch.object(
            mock_credentials, "refresh"
        ), patch.object(tm, "_save_token", return_value=True):

            # This should trigger a refresh
            tm.get_credentials()
            # The refresh logic is internal to the class

    @pytest.mark.unit
    def test_token_refresh_failure(self, mock_config, mock_credentials):
        """Test token refresh failure handling."""
        with patch("os.path.exists", return_value=True), patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_credentials,
        ):
            manager = token_manager.TokenManager(
                config=mock_config,
                credentials_file="test_creds.json",
                token_file="test_token.json",
            )

            # Test refresh failure
            mock_credentials.expired = True
            mock_credentials.refresh_token = "refresh_token"

            with patch("google.auth.transport.requests.Request"):
                mock_credentials.refresh.side_effect = Exception("Refresh failed")

                result = manager.get_credentials()
                assert result is None

    @pytest.mark.unit
    def test_check_token_expiration_no_expiry(self, mock_config, mock_credentials):
        """Test check_token_expiration with no expiry info."""
        manager = token_manager.TokenManager(
            config=mock_config,
            credentials_file="test_creds.json",
            token_file="test_token.json",
        )

        # Test credentials with no expiry
        mock_credentials.expiry = None
        with patch.object(manager, "get_credentials", return_value=mock_credentials):
            needs_refresh, expiry = manager.check_token_expiration()
            assert needs_refresh is False
            assert expiry is None

    @pytest.mark.unit
    def test_initiate_auth_flow_missing_credentials_file(self, mock_config):
        """Test initiate_auth_flow with missing credentials file."""
        manager = token_manager.TokenManager(
            config=mock_config,
            credentials_file="nonexistent.json",
            token_file="test_token.json",
        )

        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Credentials file not found"):
                manager.initiate_auth_flow()

    @pytest.mark.unit
    def test_load_existing_token_failure(self, mock_config):
        """Test loading existing token with file corruption."""
        with patch("os.path.exists", return_value=True), patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            side_effect=Exception("Corrupted token file"),
        ):
            manager = token_manager.TokenManager(
                config=mock_config,
                credentials_file="test_creds.json",
                token_file="test_token.json",
            )

            result = manager.get_credentials()
            assert result is None

    @pytest.mark.unit
    def test_global_token_manager_initialization(self):
        """Test global token manager initialization."""
        # Reset global token manager
        token_manager._global_token_manager = None

        with patch("os.environ.get") as mock_env, patch(
            "builtins.open", mock_open(read_data='{"SCOPES": ["test"]}')
        ):
            mock_env.side_effect = lambda key, default=None: {
                "CONFIG_PATH": "config.json",
                "TOKEN_PATH": "custom_token.json",
                "GOOGLE_CREDENTIALS_PATH": "custom_creds.json",
            }.get(key, default)

            manager = token_manager._get_global_token_manager()
            assert manager is not None
            assert manager.token_file == "custom_token.json"
            assert manager.credentials_file == "custom_creds.json"

    @pytest.mark.unit
    def test_global_token_manager_config_fallback(self):
        """Test global token manager with config file fallback."""
        # Reset global token manager
        token_manager._global_token_manager = None

        with patch("os.environ.get") as mock_env, patch(
            "builtins.open", side_effect=FileNotFoundError
        ):
            mock_env.side_effect = lambda key, default=None: {
                "TOKEN_PATH": "fallback_token.json",
                "GOOGLE_CREDENTIALS_PATH": "fallback_creds.json",
            }.get(key, default)

            manager = token_manager._get_global_token_manager()
            assert manager is not None
            # Should use fallback config with default scopes

    @pytest.mark.unit
    def test_load_token_function(self):
        """Test load_token utility function."""
        with patch.object(token_manager, "_get_global_token_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_credentials.return_value = "test_credentials"
            mock_get_manager.return_value = mock_manager

            result = token_manager.load_token()
            assert result == "test_credentials"
            mock_manager.get_credentials.assert_called_once()

    @pytest.mark.unit
    def test_save_token_function(self):
        """Test save_token utility function."""
        with patch.object(token_manager, "_get_global_token_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            token_manager.save_token("test_credentials")
            # The function sets _credentials and calls _save_token() without args
            assert mock_manager._credentials == "test_credentials"
            mock_manager._save_token.assert_called_once_with()

    @pytest.mark.unit
    def test_delete_token_function(self):
        """Test delete_token utility function."""
        with patch.object(token_manager, "_get_global_token_manager") as mock_get_manager, patch(
            "os.path.exists", return_value=True
        ), patch("os.remove") as mock_remove:
            mock_manager = MagicMock()
            mock_manager.token_file = "test_token.json"
            mock_get_manager.return_value = mock_manager

            token_manager.delete_token()
            mock_remove.assert_called_once_with("test_token.json")

    @pytest.mark.unit
    def test_get_credentials_cached(self, mock_config, mock_credentials):
        """Test get_credentials returns cached credentials."""
        manager = token_manager.TokenManager(
            config=mock_config,
            credentials_file="test_creds.json",
            token_file="test_token.json",
        )

        # Set cached credentials
        manager._credentials = mock_credentials
        mock_credentials.valid = True

        result = manager.get_credentials()
        assert result == mock_credentials

    @pytest.mark.unit
    def test_load_token_exception(self):
        """Test load_token with exception handling."""
        with patch.object(
            token_manager,
            "_get_global_token_manager",
            side_effect=Exception("Test error"),
        ):
            result = token_manager.load_token()
            assert result is None

    @pytest.mark.unit
    def test_save_token_exception(self):
        """Test save_token with exception handling."""
        with patch.object(
            token_manager,
            "_get_global_token_manager",
            side_effect=Exception("Test error"),
        ):
            # Should not raise exception
            token_manager.save_token("test_credentials")

    @pytest.mark.unit
    def test_delete_token_exception(self):
        """Test delete_token with exception handling."""
        with patch.object(
            token_manager,
            "_get_global_token_manager",
            side_effect=Exception("Test error"),
        ):
            # Should not raise exception
            token_manager.delete_token()

    @pytest.mark.unit
    def test_delete_token_file_not_found(self):
        """Test delete_token when file doesn't exist."""
        with patch.object(token_manager, "_get_global_token_manager") as mock_get_manager, patch(
            "os.path.exists", return_value=False
        ):
            mock_manager = MagicMock()
            mock_manager.token_file = "nonexistent_token.json"
            mock_get_manager.return_value = mock_manager

            # Should not raise exception
            token_manager.delete_token()

    @pytest.mark.unit
    def test_token_refresh_success_path(self, mock_config, mock_credentials):
        """Test successful token refresh path."""
        with patch("os.path.exists", return_value=True), patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_credentials,
        ):
            manager = token_manager.TokenManager(
                config=mock_config,
                credentials_file="test_creds.json",
                token_file="test_token.json",
            )

            # Test successful refresh
            mock_credentials.expired = True
            mock_credentials.refresh_token = "refresh_token"

            with patch("google.auth.transport.requests.Request"), patch.object(
                manager, "_save_token"
            ) as mock_save:
                mock_credentials.refresh.return_value = None  # Successful refresh

                result = manager.get_credentials()
                assert result == mock_credentials
                mock_save.assert_called_once()

    @pytest.mark.unit
    def test_save_token_method(self, mock_config, mock_credentials):
        """Test _save_token method."""
        manager = token_manager.TokenManager(
            config=mock_config,
            credentials_file="test_creds.json",
            token_file="test_token.json",
        )

        manager._credentials = mock_credentials
        mock_credentials.to_json.return_value = '{"token": "test"}'

        with patch("builtins.open", mock_open()) as mock_file:
            manager._save_token()
            mock_file.assert_called_once_with("test_token.json", "w")
            mock_file().write.assert_called_once_with('{"token": "test"}')

    @pytest.mark.unit
    def test_complete_auth_flow_exception(self, mock_config):
        """Test complete_auth_flow with exception."""
        manager = token_manager.TokenManager(
            config=mock_config,
            credentials_file="test_creds.json",
            token_file="test_token.json",
        )

        # Test with exception during flow completion
        with patch.object(manager, "initiate_auth_flow", side_effect=Exception("Flow error")):
            result = manager.complete_auth_flow("test_code")
            assert result is False
