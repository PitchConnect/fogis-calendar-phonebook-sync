"""Tests for the docker_orchestrator module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import docker_orchestrator


@pytest.fixture
def service_config():
    """Return a mock service configuration."""
    return {
        "compose_file": "docker-compose.yml",
        "compose_dir": "./",
        "health_endpoint": "http://localhost:5000/health",
        "dependencies": [],
    }


@pytest.mark.integration
def test_run_command():
    """Test running a shell command."""
    # Create a real subprocess result for testing
    test_command = ["echo", "hello"]

    # Call the function under test with a real command
    with patch.object(docker_orchestrator, "logger"):
        exit_code, stdout, stderr = docker_orchestrator.run_command(test_command)

        # Verify the results for a successful command
        assert exit_code == 0
        assert "hello" in stdout
        assert stderr == ""

    # Test with a command that should fail - using a more reliable approach
    with patch.object(docker_orchestrator, "logger"):
        # Using a command that will definitely fail on any system
        exit_code, stdout, stderr = docker_orchestrator.run_command(["false"])

        # Verify the results for a failed command
        assert exit_code == 1


@pytest.mark.integration
def test_check_service_health():
    """Test checking service health."""
    # Mock the requests.get method
    with patch("requests.get") as mock_get, patch("time.sleep"):
        # Configure the mock for success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function under test with minimal retries for speed
        with patch.object(docker_orchestrator, "logger"):
            result = docker_orchestrator.check_service_health(
                "test-service", "http://localhost:5000/health", max_retries=1, retry_delay=0.1
            )

            # Verify the result
            assert result is True

            # Test with a failed health check
            mock_response.status_code = 500
            result = docker_orchestrator.check_service_health(
                "test-service", "http://localhost:5000/health", max_retries=1, retry_delay=0.1
            )
            assert result is False

            # Test with a connection error
            mock_get.side_effect = requests.exceptions.ConnectionError()
            result = docker_orchestrator.check_service_health(
                "test-service", "http://localhost:5000/health", max_retries=1, retry_delay=0.1
            )
            assert result is False


@pytest.mark.integration
# pylint: disable=redefined-outer-name
def test_start_service(service_config):
    """Test starting a service."""
    # Use the fixture parameter directly

    # Mock the run_command function
    with patch.object(docker_orchestrator, "run_command") as mock_run_command:
        # Configure the mock
        mock_run_command.side_effect = [
            (0, "stdout", ""),  # build command
            (0, "stdout", ""),  # up command
        ]

        # Mock the check_service_health function
        with patch.object(docker_orchestrator, "check_service_health", return_value=True):
            # Call the function under test
            with patch.object(docker_orchestrator, "logger"):
                result = docker_orchestrator.start_service("test-service", service_config)

                # Verify the result
                assert result is True

                # Verify the commands that were run
                assert mock_run_command.call_count == 2
                build_cmd = mock_run_command.call_args_list[0][0][0]
                assert "docker" in build_cmd[0]
                assert "build" in build_cmd

                up_cmd = mock_run_command.call_args_list[1][0][0]
                assert "docker" in up_cmd[0]
                assert "up" in up_cmd
                assert "-d" in up_cmd


@pytest.mark.integration
def test_start_service_missing_compose_file():
    """Test start_service with missing compose file."""
    service_config = {
        "compose_file": "nonexistent.yml",
        "compose_dir": "./",
        "health_endpoint": None,
        "dependencies": [],
    }

    with patch.object(docker_orchestrator, "logger"):
        result = docker_orchestrator.start_service("test-service", service_config)
        assert result is False


@pytest.mark.integration
def test_start_service_build_failure(service_config):
    """Test start_service when build fails."""
    with patch.object(docker_orchestrator, "run_command") as mock_run_command:
        # Configure build to fail
        mock_run_command.side_effect = [
            (1, "", "Build failed"),  # build command fails
        ]

        with patch.object(docker_orchestrator, "logger"):
            result = docker_orchestrator.start_service("test-service", service_config)
            assert result is False


@pytest.mark.integration
def test_start_service_startup_failure(service_config):
    """Test start_service when startup fails."""
    with patch.object(docker_orchestrator, "run_command") as mock_run_command:
        # Configure startup to fail
        mock_run_command.side_effect = [
            (0, "stdout", ""),  # build succeeds
            (1, "", "Startup failed"),  # up command fails
        ]

        with patch.object(docker_orchestrator, "logger"):
            result = docker_orchestrator.start_service("test-service", service_config)
            assert result is False


@pytest.mark.integration
def test_check_service_health_retries():
    """Test service health check with retries."""
    with patch("requests.get") as mock_get:
        # Configure to fail twice, then succeed
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        with patch.object(docker_orchestrator, "logger"), patch("time.sleep"):
            result = docker_orchestrator.check_service_health(
                "test-service", "http://localhost:5000/health", max_retries=3, retry_delay=0.1
            )
            assert result is True
            assert mock_get.call_count == 3


@pytest.mark.integration
def test_check_service_health_max_retries_exceeded():
    """Test service health check when max retries exceeded."""
    with patch("requests.get") as mock_get:
        # Configure to always fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with patch.object(docker_orchestrator, "logger"), patch("time.sleep"):
            result = docker_orchestrator.check_service_health(
                "test-service", "http://localhost:5000/health", max_retries=2, retry_delay=0.1
            )
            assert result is False
            assert mock_get.call_count == 2


@pytest.mark.integration
def test_run_command_exception():
    """Test run_command with exception."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.side_effect = Exception("Command failed")

        with patch.object(docker_orchestrator, "logger"):
            exit_code, stdout, stderr = docker_orchestrator.run_command(["test"])
            assert exit_code == 1
            assert stdout == ""
            assert "Command failed" in stderr
