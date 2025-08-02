"""Tests for run_with_headless_auth module - working tests only."""

import json
import subprocess
from unittest.mock import MagicMock, mock_open, patch

import run_with_headless_auth


class TestLoadConfig:
    """Test cases for load_config function."""

    def test_load_config_success(self):
        """Test successful config loading."""
        mock_config = {"test": "config", "key": "value"}

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
            result = run_with_headless_auth.load_config()

        assert result == mock_config

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.load_config()

        assert result == {}
        mock_logger.error.assert_called_once()

    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.load_config()

        assert result == {}
        mock_logger.error.assert_called_once()

    def test_load_config_permission_error(self):
        """Test config loading with permission error."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.load_config()

        assert result == {}
        mock_logger.error.assert_called_once()


class TestCheckDependencies:
    """Test cases for check_dependencies function."""

    def test_check_dependencies_all_present(self):
        """Test dependency check when all files are present."""
        with patch("os.path.exists", return_value=True):
            result = run_with_headless_auth.check_dependencies()

        assert result is True

    def test_check_dependencies_missing_required_files(self):
        """Test dependency check with missing required files."""

        def mock_exists(path):
            # Only config.json exists
            return path == "config.json"

        with patch("os.path.exists", side_effect=mock_exists), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.check_dependencies()

        assert result is False
        mock_logger.error.assert_called_once()
        # Check that the error message contains missing files
        error_call = mock_logger.error.call_args[0][0]
        assert "Missing required files" in error_call

    def test_check_dependencies_missing_credentials_warning(self):
        """Test dependency check with missing credentials file (warning only)."""

        def mock_exists(path):
            # All required files exist except credentials.json
            return path != "credentials.json"

        with patch("os.path.exists", side_effect=mock_exists), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.check_dependencies()

        assert result is True  # Should still return True
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "credentials.json not found" in warning_call

    def test_check_dependencies_partial_missing(self):
        """Test dependency check with some files missing."""

        def mock_exists(path):
            # Only config.json and fogis_calendar_sync.py exist
            return path in ["config.json", "fogis_calendar_sync.py"]

        with patch("os.path.exists", side_effect=mock_exists), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.check_dependencies()

        assert result is False
        mock_logger.error.assert_called_once()


class TestSetupHeadlessMonitoring:
    """Test cases for setup_headless_monitoring function."""

    def test_setup_headless_monitoring_success(self):
        """Test successful headless monitoring setup."""
        mock_config = {"test": "config"}
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_token_status.return_value = {
            "valid": True,
            "needs_refresh": False,
        }

        with patch("run_with_headless_auth.load_config", return_value=mock_config), patch(
            "headless_auth.HeadlessAuthManager", return_value=mock_auth_manager
        ), patch("run_with_headless_auth.logger") as mock_logger:

            result = run_with_headless_auth.setup_headless_monitoring()

        assert result == mock_auth_manager
        mock_auth_manager.start_monitoring.assert_called_once()
        mock_logger.info.assert_any_call("Started background token monitoring")

    def test_setup_headless_monitoring_needs_refresh(self):
        """Test headless monitoring setup when token needs refresh."""
        mock_config = {"test": "config"}
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_token_status.return_value = {
            "valid": False,
            "needs_refresh": True,
        }
        mock_credentials = MagicMock()
        mock_auth_manager.get_valid_credentials.return_value = mock_credentials

        with patch("run_with_headless_auth.load_config", return_value=mock_config), patch(
            "headless_auth.HeadlessAuthManager", return_value=mock_auth_manager
        ), patch("run_with_headless_auth.logger") as mock_logger:

            result = run_with_headless_auth.setup_headless_monitoring()

        assert result == mock_auth_manager
        mock_auth_manager.get_valid_credentials.assert_called_once()
        mock_auth_manager.start_monitoring.assert_called_once()
        mock_logger.info.assert_any_call("Token needs refresh - starting headless authentication")

    def test_setup_headless_monitoring_credentials_failure(self):
        """Test headless monitoring setup when credentials fail."""
        mock_config = {"test": "config"}
        mock_auth_manager = MagicMock()
        mock_auth_manager.get_token_status.return_value = {
            "valid": False,
            "needs_refresh": True,
        }
        mock_auth_manager.get_valid_credentials.return_value = None  # Failure

        with patch("run_with_headless_auth.load_config", return_value=mock_config), patch(
            "headless_auth.HeadlessAuthManager", return_value=mock_auth_manager
        ), patch("run_with_headless_auth.logger") as mock_logger:

            result = run_with_headless_auth.setup_headless_monitoring()

        assert result is None
        mock_auth_manager.get_valid_credentials.assert_called_once()
        mock_auth_manager.start_monitoring.assert_not_called()
        mock_logger.error.assert_called_with("Failed to get valid credentials")

    def test_setup_headless_monitoring_import_error(self):
        """Test headless monitoring setup with import error."""
        with patch("run_with_headless_auth.load_config"), patch(
            "headless_auth.HeadlessAuthManager",
            side_effect=ImportError("Module not found"),
        ), patch("run_with_headless_auth.logger") as mock_logger:

            result = run_with_headless_auth.setup_headless_monitoring()

        assert result is None
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to import headless auth modules" in error_call


class TestRunCalendarSync:
    """Test cases for run_calendar_sync function."""

    def test_run_calendar_sync_success(self):
        """Test successful calendar sync execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Sync completed successfully"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.run_calendar_sync()

        assert result is True
        mock_logger.info.assert_any_call("Starting FOGIS Calendar Sync...")
        mock_logger.info.assert_any_call("Calendar sync completed successfully")

    def test_run_calendar_sync_failure(self):
        """Test calendar sync execution failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Sync failed with error"

        with patch("subprocess.run", return_value=mock_result), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.run_calendar_sync()

        assert result is False
        mock_logger.error.assert_any_call("Calendar sync failed with return code 1")
        mock_logger.error.assert_any_call("Error: Sync failed with error")

    def test_run_calendar_sync_exception(self):
        """Test calendar sync with subprocess exception."""
        with patch("subprocess.run", side_effect=Exception("Subprocess error")), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.run_calendar_sync()

        assert result is False
        mock_logger.exception.assert_called()

    def test_run_calendar_sync_with_output(self):
        """Test calendar sync with stdout output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Detailed sync output"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.run_calendar_sync()

        assert result is True
        mock_logger.info.assert_any_call("Output: Detailed sync output")


class TestMain:
    """Test cases for main function."""

    def test_main_success_with_headless_auth(self):
        """Test successful main execution with headless auth."""
        mock_auth_manager = MagicMock()

        with patch("run_with_headless_auth.check_dependencies", return_value=True), patch(
            "run_with_headless_auth.setup_headless_monitoring",
            return_value=mock_auth_manager,
        ), patch("run_with_headless_auth.run_calendar_sync", return_value=True), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 0
        mock_logger.info.assert_any_call(
            "🚀 Starting FOGIS Calendar Sync with Headless Authentication"
        )
        mock_logger.info.assert_any_call("✅ Headless authentication monitoring active")
        mock_logger.info.assert_any_call("✅ Calendar sync completed successfully")

    def test_main_success_without_headless_auth(self):
        """Test successful main execution without headless auth."""
        with patch("run_with_headless_auth.check_dependencies", return_value=True), patch(
            "run_with_headless_auth.setup_headless_monitoring", return_value=None
        ), patch("run_with_headless_auth.run_calendar_sync", return_value=True), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 0
        mock_logger.warning.assert_any_call(
            "⚠️  Headless authentication not available - running without it"
        )
        mock_logger.info.assert_any_call("✅ Calendar sync completed successfully")

    def test_main_dependency_check_failure(self):
        """Test main execution when dependency check fails."""
        with patch("run_with_headless_auth.check_dependencies", return_value=False), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 1
        mock_logger.error.assert_any_call("❌ Dependency check failed")

    def test_main_calendar_sync_failure(self):
        """Test main execution when calendar sync fails."""
        mock_auth_manager = MagicMock()

        with patch("run_with_headless_auth.check_dependencies", return_value=True), patch(
            "run_with_headless_auth.setup_headless_monitoring",
            return_value=mock_auth_manager,
        ), patch("run_with_headless_auth.run_calendar_sync", return_value=False), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 1
        mock_logger.error.assert_any_call("❌ Calendar sync failed")

    def test_main_keyboard_interrupt(self):
        """Test main execution with keyboard interrupt."""
        with patch("run_with_headless_auth.check_dependencies", return_value=True), patch(
            "run_with_headless_auth.setup_headless_monitoring", return_value=None
        ), patch("run_with_headless_auth.run_calendar_sync", side_effect=KeyboardInterrupt), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 0  # KeyboardInterrupt returns 0
        mock_logger.info.assert_any_call("Interrupted by user")

    def test_main_unexpected_exception(self):
        """Test main execution with unexpected exception."""
        with patch("run_with_headless_auth.check_dependencies", return_value=True), patch(
            "run_with_headless_auth.setup_headless_monitoring", return_value=None
        ), patch(
            "run_with_headless_auth.run_calendar_sync",
            side_effect=Exception("Unexpected error"),
        ), patch(
            "run_with_headless_auth.logger"
        ) as mock_logger:

            result = run_with_headless_auth.main()

        assert result == 1
        mock_logger.exception.assert_called()


# All tests are now stable and reliable!
