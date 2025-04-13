"""Tests for the docker_orchestrator module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import docker_orchestrator


@pytest.fixture
def mock_service_config():
    """Return a mock service configuration."""
    return {
        "compose_file": "docker-compose.yml",
        "compose_dir": "./",
        "health_endpoint": "http://localhost:5000/health",
        "dependencies": []
    }


@pytest.mark.unit
def test_run_command():
    """Test running a shell command."""
    # Mock the subprocess.Popen
    with patch("subprocess.Popen") as mock_popen:
        # Configure the mock
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("stdout output", "stderr output")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Call the function under test
        with patch.object(docker_orchestrator, "logger"):
            exit_code, stdout, stderr = docker_orchestrator.run_command(["echo", "hello"])

            # Verify the results
            assert exit_code == 0
            assert stdout == "stdout output"
            assert stderr == "stderr output"

            # Test with a non-zero exit code
            mock_process.returncode = 1
            exit_code, stdout, stderr = docker_orchestrator.run_command(["echo", "error"])
            assert exit_code == 1


@pytest.mark.unit
def test_check_service_health():
    """Test checking service health."""
    # Mock the requests.get method
    with patch("requests.get") as mock_get:
        # Configure the mock for success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function under test
        with patch.object(docker_orchestrator, "logger"):
            result = docker_orchestrator.check_service_health("test-service", "http://localhost:5000/health")

            # Verify the result
            assert result is True

            # Test with a failed health check
            mock_response.status_code = 500
            result = docker_orchestrator.check_service_health("test-service", "http://localhost:5000/health")
            assert result is False

            # Test with a connection error
            mock_get.side_effect = requests.exceptions.ConnectionError()
            result = docker_orchestrator.check_service_health("test-service", "http://localhost:5000/health")
            assert result is False


@pytest.mark.unit
def test_start_service(mock_service_config):
    """Test starting a service."""
    # Mock the run_command function
    with patch.object(docker_orchestrator, "run_command") as mock_run_command:
        # Configure the mock
        mock_run_command.side_effect = [
            (0, "stdout", ""),  # build command
            (0, "stdout", "")   # up command
        ]

        # Mock the check_service_health function
        with patch.object(docker_orchestrator, "check_service_health", return_value=True):
            # Call the function under test
            with patch.object(docker_orchestrator, "logger"):
                result = docker_orchestrator.start_service("test-service", mock_service_config)

                # Verify the result
                assert result is True

                # Verify the commands that were run
                assert mock_run_command.call_count == 2
                build_cmd = mock_run_command.call_args_list[0][0][0]
                assert "docker-compose" in build_cmd[0]
                assert "build" in build_cmd

                up_cmd = mock_run_command.call_args_list[1][0][0]
                assert "docker-compose" in up_cmd[0]
                assert "up" in up_cmd
                assert "-d" in up_cmd
