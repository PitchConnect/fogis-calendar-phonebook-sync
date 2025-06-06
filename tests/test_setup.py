"""Comprehensive tests for setup.py module."""

import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

import setup


class TestColors:
    """Test cases for Colors class."""

    def test_colors_class_attributes(self):
        """Test that Colors class has all required ANSI color codes."""
        assert hasattr(setup.Colors, "HEADER")
        assert hasattr(setup.Colors, "BLUE")
        assert hasattr(setup.Colors, "GREEN")
        assert hasattr(setup.Colors, "YELLOW")
        assert hasattr(setup.Colors, "RED")
        assert hasattr(setup.Colors, "ENDC")
        assert hasattr(setup.Colors, "BOLD")
        assert hasattr(setup.Colors, "UNDERLINE")

        # Verify they are ANSI escape sequences
        assert setup.Colors.HEADER.startswith("\033[")
        assert setup.Colors.GREEN.startswith("\033[")
        assert setup.Colors.ENDC == "\033[0m"


class TestPrintFunctions:
    """Test cases for print functions."""

    @patch("builtins.print")
    def test_print_header(self, mock_print):
        """Test print_header function."""
        setup.print_header("Test Header")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Test Header" in call_args
        assert setup.Colors.HEADER in call_args
        assert setup.Colors.BOLD in call_args

    @patch("builtins.print")
    def test_print_success(self, mock_print):
        """Test print_success function."""
        setup.print_success("Success message")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Success message" in call_args
        assert setup.Colors.GREEN in call_args
        assert "✓" in call_args

    @patch("builtins.print")
    def test_print_warning(self, mock_print):
        """Test print_warning function."""
        setup.print_warning("Warning message")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Warning message" in call_args
        assert setup.Colors.YELLOW in call_args
        assert "⚠" in call_args

    @patch("builtins.print")
    def test_print_error(self, mock_print):
        """Test print_error function."""
        setup.print_error("Error message")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Error message" in call_args
        assert setup.Colors.RED in call_args
        assert "✗" in call_args

    @patch("builtins.print")
    def test_print_info(self, mock_print):
        """Test print_info function."""
        setup.print_info("Info message")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Info message" in call_args
        assert setup.Colors.BLUE in call_args
        assert "ℹ" in call_args


class TestCheckWritePermission:
    """Test cases for check_write_permission function."""

    @patch("tempfile.NamedTemporaryFile")
    def test_check_write_permission_success(self, mock_temp_file):
        """Test successful write permission check."""
        mock_temp_file.return_value.__enter__.return_value = MagicMock()

        result = setup.check_write_permission("/tmp")

        assert result is True
        mock_temp_file.assert_called_once_with(dir="/tmp", delete=True)

    @patch("tempfile.NamedTemporaryFile")
    def test_check_write_permission_failure(self, mock_temp_file):
        """Test failed write permission check."""
        mock_temp_file.side_effect = OSError("Permission denied")

        result = setup.check_write_permission("/root")

        assert result is False

    def test_check_write_permission_with_real_temp_dir(self):
        """Test write permission check with real temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = setup.check_write_permission(temp_dir)
            assert result is True


class TestCheckPermissions:
    """Test cases for check_permissions function."""

    @patch("setup.check_write_permission")
    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("os.getcwd")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.remove")
    def test_check_permissions_success(
        self,
        mock_remove,
        mock_file,
        mock_getcwd,
        mock_print_success,
        mock_print_header,
        mock_check_write,
    ):
        """Test successful permission checks."""
        mock_getcwd.return_value = "/test/dir"
        mock_check_write.return_value = True

        result = setup.check_permissions()

        assert result is True
        mock_print_header.assert_called_once_with("Checking Permissions")
        assert mock_print_success.call_count == 2
        mock_file.assert_called_once()
        mock_remove.assert_called_once()

    @patch("setup.check_write_permission")
    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("os.getcwd")
    def test_check_permissions_no_write_permission(
        self, mock_getcwd, mock_print_info, mock_print_error, mock_print_header, mock_check_write
    ):
        """Test permission check failure due to no write permission."""
        mock_getcwd.return_value = "/test/dir"
        mock_check_write.return_value = False

        result = setup.check_permissions()

        assert result is False
        mock_print_error.assert_called_once()
        assert mock_print_info.call_count == 2

    @patch("setup.check_write_permission")
    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("os.getcwd")
    @patch("builtins.open")
    def test_check_permissions_file_creation_error(
        self,
        mock_file,
        mock_getcwd,
        mock_print_info,
        mock_print_error,
        mock_print_success,
        mock_print_header,
        mock_check_write,
    ):
        """Test permission check failure due to file creation error."""
        mock_getcwd.return_value = "/test/dir"
        mock_check_write.return_value = True
        mock_file.side_effect = OSError("Cannot create file")

        result = setup.check_permissions()

        assert result is False
        mock_print_success.assert_called_once()
        mock_print_error.assert_called_once()
        assert mock_print_info.call_count == 2


class TestRunCommand:
    """Test cases for run_command function."""

    @patch("subprocess.run")
    def test_run_command_success_with_list(self, mock_subprocess):
        """Test successful command execution with command as list."""
        mock_result = MagicMock()
        mock_result.stdout = "Command output"
        mock_subprocess.return_value = mock_result

        success, output = setup.run_command(["echo", "hello"])

        assert success is True
        assert output == "Command output"
        mock_subprocess.assert_called_once_with(
            ["echo", "hello"], shell=False, check=True, text=True, capture_output=True, cwd=None
        )

    @patch("subprocess.run")
    @patch("shlex.split")
    def test_run_command_success_with_string(self, mock_shlex, mock_subprocess):
        """Test successful command execution with command as string."""
        mock_shlex.return_value = ["echo", "hello"]
        mock_result = MagicMock()
        mock_result.stdout = "Command output"
        mock_subprocess.return_value = mock_result

        success, output = setup.run_command("echo hello")

        assert success is True
        assert output == "Command output"
        mock_shlex.assert_called_once_with("echo hello")

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_subprocess):
        """Test failed command execution."""
        from subprocess import CalledProcessError

        error = CalledProcessError(1, "command")
        error.stderr = "Command failed"
        mock_subprocess.side_effect = error

        success, output = setup.run_command(["false"])

        assert success is False
        assert output == "Command failed"

    @patch("subprocess.run")
    def test_run_command_with_cwd(self, mock_subprocess):
        """Test command execution with custom working directory."""
        mock_result = MagicMock()
        mock_result.stdout = "Output"
        mock_subprocess.return_value = mock_result

        success, output = setup.run_command(["pwd"], cwd="/tmp")

        assert success is True
        mock_subprocess.assert_called_once_with(
            ["pwd"], shell=False, check=True, text=True, capture_output=True, cwd="/tmp"
        )


class TestCheckPythonVersion:
    """Test cases for check_python_version function."""

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("sys.version_info")
    def test_check_python_version_valid(self, mock_version, mock_print_success, mock_print_header):
        """Test Python version check with valid version."""
        mock_version.major = 3
        mock_version.minor = 9
        mock_version.micro = 0

        result = setup.check_python_version()

        assert result is True
        mock_print_header.assert_called_once_with("Checking Python Version")
        mock_print_success.assert_called_once()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("sys.version_info")
    def test_check_python_version_invalid(self, mock_version, mock_print_error, mock_print_header):
        """Test Python version check with invalid version."""
        mock_version.major = 3
        mock_version.minor = 5
        mock_version.micro = 0

        result = setup.check_python_version()

        assert result is False
        mock_print_error.assert_called_once()

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("sys.version_info")
    def test_check_python_version_minimum_valid(
        self, mock_version, mock_print_success, mock_print_header
    ):
        """Test Python version check with minimum valid version."""
        mock_version.major = 3
        mock_version.minor = 6
        mock_version.micro = 0

        result = setup.check_python_version()

        assert result is True


class TestCheckRequiredFiles:
    """Test cases for check_required_files function."""

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("os.path.exists")
    def test_check_required_files_all_exist(
        self, mock_exists, mock_print_success, mock_print_header
    ):
        """Test when all required files exist."""
        mock_exists.return_value = True

        result = setup.check_required_files()

        assert result is True
        mock_print_header.assert_called_once_with("Checking Required Files")
        # Should be called for config.json, requirements.txt, credentials.json, .env
        assert mock_print_success.call_count == 4

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("os.path.exists")
    def test_check_required_files_missing_config(
        self, mock_exists, mock_print_error, mock_print_header
    ):
        """Test when config.json is missing."""

        def exists_side_effect(path):
            return path != "config.json"

        mock_exists.side_effect = exists_side_effect

        result = setup.check_required_files()

        assert result is False
        mock_print_error.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_warning")
    @patch("setup.print_info")
    @patch("os.path.exists")
    def test_check_required_files_missing_credentials(
        self, mock_exists, mock_print_info, mock_print_warning, mock_print_header
    ):
        """Test when credentials.json is missing."""

        def exists_side_effect(path):
            if path == "credentials.json":
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        result = setup.check_required_files()

        assert result is False
        mock_print_warning.assert_called()
        assert mock_print_info.call_count >= 2

    @patch("setup.print_header")
    @patch("setup.print_warning")
    @patch("setup.print_info")
    @patch("os.path.exists")
    def test_check_required_files_missing_env_with_example(
        self, mock_exists, mock_print_info, mock_print_warning, mock_print_header
    ):
        """Test when .env is missing but .env.example exists."""

        def exists_side_effect(path):
            if path == ".env":
                return False
            elif path == ".env.example":
                return True
            return True

        mock_exists.side_effect = exists_side_effect

        result = setup.check_required_files()

        assert result is False
        mock_print_warning.assert_called()
        mock_print_info.assert_called()


class TestSetupVirtualEnvironment:
    """Test cases for setup_virtual_environment function."""

    @patch("setup.print_header")
    @patch("setup.print_info")
    @patch("builtins.input")
    @patch("os.path.exists")
    @patch("platform.system")
    def test_setup_virtual_environment_exists_activate_yes(
        self, mock_platform, mock_exists, mock_input, mock_print_info, mock_print_header
    ):
        """Test when virtual environment exists and user wants to activate."""
        mock_exists.return_value = True
        mock_input.return_value = "y"
        mock_platform.return_value = "Linux"

        result = setup.setup_virtual_environment()

        assert result is True
        mock_print_header.assert_called_once_with("Setting Up Virtual Environment")
        assert mock_print_info.call_count >= 2

    @patch("setup.print_header")
    @patch("setup.print_info")
    @patch("builtins.input")
    @patch("os.path.exists")
    def test_setup_virtual_environment_exists_activate_no(
        self, mock_exists, mock_input, mock_print_info, mock_print_header
    ):
        """Test when virtual environment exists and user doesn't want to activate."""
        mock_exists.return_value = True
        mock_input.return_value = "n"

        result = setup.setup_virtual_environment()

        assert result is True
        mock_print_info.assert_called_once()

    @patch("setup.print_header")
    @patch("setup.print_info")
    @patch("setup.print_success")
    @patch("setup.check_write_permission")
    @patch("setup.run_command")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("os.path.abspath")
    @patch("platform.system")
    @patch("sys.executable", "/usr/bin/python3")
    def test_setup_virtual_environment_create_success(
        self,
        mock_platform,
        mock_abspath,
        mock_dirname,
        mock_exists,
        mock_run_command,
        mock_check_write,
        mock_print_success,
        mock_print_info,
        mock_print_header,
    ):
        """Test successful virtual environment creation."""
        mock_exists.return_value = False
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/venv"
        mock_check_write.return_value = True
        mock_run_command.return_value = (True, "Virtual environment created")
        mock_platform.return_value = "Linux"

        result = setup.setup_virtual_environment()

        assert result is True
        mock_run_command.assert_called_once_with("/usr/bin/python3 -m venv venv")
        mock_print_success.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("setup.check_write_permission")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("os.path.abspath")
    def test_setup_virtual_environment_no_permission(
        self,
        mock_abspath,
        mock_dirname,
        mock_exists,
        mock_check_write,
        mock_print_info,
        mock_print_error,
        mock_print_header,
    ):
        """Test virtual environment creation without permission."""
        mock_exists.return_value = False
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/venv"
        mock_check_write.return_value = False

        result = setup.setup_virtual_environment()

        assert result is False
        mock_print_error.assert_called()
        assert mock_print_info.call_count >= 2

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.check_write_permission")
    @patch("setup.run_command")
    @patch("os.path.exists")
    @patch("os.path.dirname")
    @patch("os.path.abspath")
    def test_setup_virtual_environment_create_failure(
        self,
        mock_abspath,
        mock_dirname,
        mock_exists,
        mock_run_command,
        mock_check_write,
        mock_print_error,
        mock_print_header,
    ):
        """Test failed virtual environment creation."""
        mock_exists.return_value = False
        mock_dirname.return_value = "/test"
        mock_abspath.return_value = "/test/venv"
        mock_check_write.return_value = True
        mock_run_command.return_value = (False, "Creation failed")

        result = setup.setup_virtual_environment()

        assert result is False
        mock_print_error.assert_called_with("Failed to create virtual environment: Creation failed")


class TestInstallDependencies:
    """Test cases for install_dependencies function."""

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("setup.run_command")
    @patch("os.path.exists")
    @patch("sys.prefix", "/venv")
    @patch("sys.base_prefix", "/usr")
    def test_install_dependencies_success(
        self, mock_exists, mock_run_command, mock_print_success, mock_print_header
    ):
        """Test successful dependency installation."""
        mock_exists.return_value = True
        mock_run_command.return_value = (True, "Dependencies installed")

        result = setup.install_dependencies()

        assert result is True
        mock_print_header.assert_called_once_with("Installing Dependencies")
        mock_print_success.assert_called_once_with("Dependencies installed successfully")

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("os.path.exists")
    def test_install_dependencies_no_requirements(
        self, mock_exists, mock_print_error, mock_print_header
    ):
        """Test when requirements.txt doesn't exist."""
        mock_exists.return_value = False

        result = setup.install_dependencies()

        assert result is False
        mock_print_error.assert_called_once_with("requirements.txt not found")

    @patch("setup.print_header")
    @patch("setup.print_warning")
    @patch("setup.print_info")
    @patch("builtins.input")
    @patch("os.path.exists")
    @patch("sys.prefix", "/usr")
    @patch("sys.base_prefix", "/usr")
    def test_install_dependencies_not_in_venv_proceed_no(
        self, mock_exists, mock_input, mock_print_info, mock_print_warning, mock_print_header
    ):
        """Test when not in virtual environment and user chooses not to proceed."""
        mock_exists.return_value = True
        mock_input.return_value = "n"

        result = setup.install_dependencies()

        assert result is False
        mock_print_warning.assert_called_once_with("Not running in a virtual environment")
        mock_print_info.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_warning")
    @patch("setup.print_success")
    @patch("setup.run_command")
    @patch("builtins.input")
    @patch("os.path.exists")
    @patch("sys.prefix", "/usr")
    @patch("sys.base_prefix", "/usr")
    def test_install_dependencies_not_in_venv_proceed_yes(
        self,
        mock_exists,
        mock_input,
        mock_run_command,
        mock_print_success,
        mock_print_warning,
        mock_print_header,
    ):
        """Test when not in virtual environment and user chooses to proceed."""
        mock_exists.return_value = True
        mock_input.return_value = "y"
        mock_run_command.return_value = (True, "Dependencies installed")

        result = setup.install_dependencies()

        assert result is True
        mock_print_warning.assert_called_once_with("Not running in a virtual environment")
        mock_print_success.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.run_command")
    @patch("os.path.exists")
    @patch("sys.prefix", "/venv")
    @patch("sys.base_prefix", "/usr")
    def test_install_dependencies_failure(
        self, mock_exists, mock_run_command, mock_print_error, mock_print_header
    ):
        """Test failed dependency installation."""
        mock_exists.return_value = True
        mock_run_command.return_value = (False, "Installation failed")

        result = setup.install_dependencies()

        assert result is False
        mock_print_error.assert_called_with("Failed to install dependencies: Installation failed")


class TestSetupEnvFile:
    """Test cases for setup_env_file function."""

    @patch("setup.print_header")
    @patch("setup.print_info")
    @patch("builtins.input")
    @patch("os.path.exists")
    def test_setup_env_file_exists_no_modify(
        self, mock_exists, mock_input, mock_print_info, mock_print_header
    ):
        """Test when .env file exists and user doesn't want to modify."""
        mock_exists.return_value = True
        mock_input.return_value = "n"

        result = setup.setup_env_file()

        assert result is True
        mock_print_info.assert_called_once_with(".env file already exists")

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("setup.check_write_permission")
    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_setup_env_file_create_new(
        self,
        mock_getcwd,
        mock_exists,
        mock_file,
        mock_input,
        mock_check_write,
        mock_print_success,
        mock_print_header,
    ):
        """Test creating new .env file."""
        mock_getcwd.return_value = "/test"

        # .env doesn't exist, .env.example doesn't exist
        def exists_side_effect(path):
            return path not in [".env", ".env.example"]

        mock_exists.side_effect = exists_side_effect
        mock_check_write.return_value = True
        mock_input.side_effect = ["testuser", "testpass"]

        result = setup.setup_env_file()

        assert result is True
        mock_file.assert_called_once_with(".env", "w", encoding="utf-8")
        mock_print_success.assert_called_once_with("Environment variables saved to .env file")

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("setup.check_write_permission")
    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_setup_env_file_no_permission(
        self,
        mock_getcwd,
        mock_exists,
        mock_check_write,
        mock_print_info,
        mock_print_error,
        mock_print_header,
    ):
        """Test when no write permission for .env file."""
        mock_getcwd.return_value = "/test"
        mock_exists.return_value = False
        mock_check_write.return_value = False

        result = setup.setup_env_file()

        assert result is False
        mock_print_error.assert_called_once_with(
            "You don't have permission to create/modify the .env file"
        )
        assert mock_print_info.call_count >= 2

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("setup.check_write_permission")
    @patch("builtins.input")
    @patch("shutil.copy")
    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_setup_env_file_copy_from_example(
        self,
        mock_getcwd,
        mock_exists,
        mock_copy,
        mock_input,
        mock_check_write,
        mock_print_success,
        mock_print_header,
    ):
        """Test copying .env from .env.example."""
        mock_getcwd.return_value = "/test"

        def exists_side_effect(path):
            if path == ".env":
                return False
            elif path == ".env.example":
                return True
            return False

        mock_exists.side_effect = exists_side_effect
        mock_check_write.return_value = True
        mock_input.side_effect = ["testuser", "testpass"]

        with patch("builtins.open", mock_open()):
            result = setup.setup_env_file()

        assert result is True
        mock_copy.assert_called_once_with(".env.example", ".env")
        mock_print_success.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("setup.check_write_permission")
    @patch("builtins.input")
    @patch("builtins.open")
    @patch("os.path.exists")
    @patch("os.getcwd")
    def test_setup_env_file_write_error(
        self,
        mock_getcwd,
        mock_exists,
        mock_file,
        mock_input,
        mock_check_write,
        mock_print_info,
        mock_print_error,
        mock_print_header,
    ):
        """Test when writing .env file fails."""
        mock_getcwd.return_value = "/test"
        mock_exists.return_value = False
        mock_check_write.return_value = True
        mock_input.side_effect = ["testuser", "testpass"]
        mock_file.side_effect = OSError("Write failed")

        result = setup.setup_env_file()

        assert result is False
        mock_print_error.assert_called_with("Failed to write to .env file: Write failed")
        assert mock_print_info.call_count >= 2


class TestCheckGoogleCredentials:
    """Test cases for check_google_credentials function."""

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"installed": {"client_id": "123456.apps.googleusercontent.com"}}',
    )
    @patch("os.path.exists")
    def test_check_google_credentials_valid(
        self, mock_exists, mock_file, mock_print_success, mock_print_header
    ):
        """Test valid Google credentials file."""
        mock_exists.return_value = True

        result = setup.check_google_credentials()

        assert result is True
        mock_print_header.assert_called_once_with("Checking Google API Credentials")
        mock_print_success.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("os.path.exists")
    def test_check_google_credentials_missing_file(
        self, mock_exists, mock_print_error, mock_print_header
    ):
        """Test when credentials.json doesn't exist."""
        mock_exists.return_value = False

        result = setup.check_google_credentials()

        assert result is False
        mock_print_error.assert_called_with("credentials.json not found")

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("os.path.exists")
    def test_check_google_credentials_invalid_json(
        self, mock_exists, mock_file, mock_print_error, mock_print_header
    ):
        """Test when credentials.json contains invalid JSON."""
        mock_exists.return_value = True

        result = setup.check_google_credentials()

        assert result is False
        mock_print_error.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("os.path.exists")
    def test_check_google_credentials_missing_keys(
        self, mock_exists, mock_file, mock_print_info, mock_print_error, mock_print_header
    ):
        """Test when credentials.json is missing required keys."""
        mock_exists.return_value = True

        result = setup.check_google_credentials()

        assert result is False
        mock_print_error.assert_called()
        mock_print_info.assert_called()


class TestCheckConfigFile:
    """Test cases for check_config_file function."""

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"CREDENTIALS_FILE": "creds.json", "CALENDAR_ID": "test@gmail.com", "SYNC_TAG": "tag", "SCOPES": ["scope1"]}',
    )
    @patch("os.path.exists")
    def test_check_config_file_valid(
        self, mock_exists, mock_file, mock_print_success, mock_print_header
    ):
        """Test valid config.json file."""
        mock_exists.return_value = True

        result = setup.check_config_file()

        assert result is True
        mock_print_header.assert_called_once_with("Checking Configuration")
        mock_print_success.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("os.path.exists")
    def test_check_config_file_missing(self, mock_exists, mock_print_error, mock_print_header):
        """Test when config.json doesn't exist."""
        mock_exists.return_value = False

        result = setup.check_config_file()

        assert result is False
        mock_print_error.assert_called_with("config.json not found")

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("os.path.exists")
    def test_check_config_file_invalid_json(
        self, mock_exists, mock_file, mock_print_error, mock_print_header
    ):
        """Test when config.json contains invalid JSON."""
        mock_exists.return_value = True

        result = setup.check_config_file()

        assert result is False
        mock_print_error.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("builtins.open", new_callable=mock_open, read_data='{"CALENDAR_ID": "test@gmail.com"}')
    @patch("os.path.exists")
    def test_check_config_file_missing_keys(
        self, mock_exists, mock_file, mock_print_error, mock_print_header
    ):
        """Test when config.json is missing required keys."""
        mock_exists.return_value = True

        result = setup.check_config_file()

        assert result is False
        mock_print_error.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_success")
    @patch("setup.print_warning")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"CREDENTIALS_FILE": "creds.json", "CALENDAR_ID": "invalid-calendar", "SYNC_TAG": "tag", "SCOPES": ["scope1"]}',
    )
    @patch("os.path.exists")
    def test_check_config_file_invalid_calendar_id(
        self, mock_exists, mock_file, mock_print_warning, mock_print_success, mock_print_header
    ):
        """Test when config.json has invalid calendar ID format."""
        mock_exists.return_value = True

        result = setup.check_config_file()

        assert result is True
        mock_print_success.assert_called()
        mock_print_warning.assert_called()


class TestTestFogisConnection:
    """Test cases for test_fogis_connection function."""

    @patch("setup.print_header")
    @patch("setup.print_warning")
    @patch("setup.print_info")
    @patch("setup.run_command")
    @patch("builtins.input")
    @patch("sys.executable", "/usr/bin/python3")
    def test_test_fogis_connection_success(
        self, mock_input, mock_run_command, mock_print_info, mock_print_warning, mock_print_header
    ):
        """Test successful FOGIS connection test."""
        mock_input.return_value = "y"
        mock_run_command.return_value = (True, "Login failed")  # Expected response

        result = setup.test_fogis_connection()

        assert result is True
        mock_print_header.assert_called_once_with("Testing FOGIS Connection")
        mock_print_warning.assert_called()
        mock_print_info.assert_called()

    @patch("setup.print_header")
    @patch("setup.print_info")
    @patch("builtins.input")
    def test_test_fogis_connection_user_declines(
        self, mock_input, mock_print_info, mock_print_header
    ):
        """Test when user declines FOGIS connection test."""
        mock_input.return_value = "n"

        result = setup.test_fogis_connection()

        assert result is True
        mock_print_info.assert_called_with("Skipping FOGIS connection test")

    @patch("setup.print_header")
    @patch("setup.print_error")
    @patch("setup.print_info")
    @patch("setup.run_command")
    @patch("builtins.input")
    @patch("sys.executable", "/usr/bin/python3")
    def test_test_fogis_connection_unexpected_response(
        self, mock_input, mock_run_command, mock_print_info, mock_print_error, mock_print_header
    ):
        """Test FOGIS connection with unexpected response."""
        mock_input.return_value = "y"
        mock_run_command.return_value = (True, "Unexpected response")

        result = setup.test_fogis_connection()

        assert result is False
        mock_print_error.assert_called_with("Unexpected response from FOGIS login test")
        mock_print_info.assert_called()
