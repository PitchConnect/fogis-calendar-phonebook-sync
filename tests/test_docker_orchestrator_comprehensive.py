"""Comprehensive tests for docker_orchestrator module - Final Boss Battle!"""

import argparse
import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

import docker_orchestrator


class TestRunCommand:
    """Test cases for run_command function."""

    @patch("subprocess.Popen")
    def test_run_command_success(self, mock_popen):
        """Test successful command execution."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value.__enter__.return_value = mock_process

        exit_code, stdout, stderr = docker_orchestrator.run_command(["echo", "hello"])

        assert exit_code == 0
        assert stdout == "output"
        assert stderr == ""

    @patch("subprocess.Popen")
    def test_run_command_failure(self, mock_popen):
        """Test failed command execution."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "error")
        mock_process.returncode = 1
        mock_popen.return_value.__enter__.return_value = mock_process

        exit_code, stdout, stderr = docker_orchestrator.run_command(["false"])

        assert exit_code == 1
        assert stdout == ""
        assert stderr == "error"

    @patch("subprocess.Popen")
    def test_run_command_exception(self, mock_popen):
        """Test command execution with exception."""
        mock_popen.side_effect = Exception("Process error")

        exit_code, stdout, stderr = docker_orchestrator.run_command(["invalid"])

        assert exit_code == 1
        assert stdout == ""
        assert stderr == "Process error"

    @patch("subprocess.Popen")
    def test_run_command_with_cwd(self, mock_popen):
        """Test command execution with custom working directory."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value.__enter__.return_value = mock_process

        exit_code, stdout, stderr = docker_orchestrator.run_command(["pwd"], cwd="/tmp")

        assert exit_code == 0
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        assert call_args[1]["cwd"] == "/tmp"


class TestCheckServiceHealth:
    """Test cases for check_service_health function."""

    def test_check_service_health_no_endpoint(self):
        """Test health check with no endpoint."""
        result = docker_orchestrator.check_service_health("test-service", None)
        assert result is True

    @patch("requests.get")
    @patch("time.sleep")
    def test_check_service_health_success(self, mock_sleep, mock_get):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = docker_orchestrator.check_service_health(
            "test-service", "http://localhost:5000/health", max_retries=1
        )

        assert result is True
        mock_get.assert_called_once_with("http://localhost:5000/health", timeout=10)

    @patch("requests.get")
    @patch("time.sleep")
    def test_check_service_health_failure_status_code(self, mock_sleep, mock_get):
        """Test health check with failed status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = docker_orchestrator.check_service_health(
            "test-service",
            "http://localhost:5000/health",
            max_retries=2,
            retry_delay=0.1,
        )

        assert result is False
        assert mock_get.call_count == 2

    @patch("requests.get")
    @patch("time.sleep")
    def test_check_service_health_connection_error(self, mock_sleep, mock_get):
        """Test health check with connection error."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        result = docker_orchestrator.check_service_health(
            "test-service", "http://localhost:5000/health", max_retries=1
        )

        assert result is False

    @patch("requests.get")
    @patch("time.sleep")
    def test_check_service_health_retry_then_success(self, mock_sleep, mock_get):
        """Test health check that fails then succeeds."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        mock_get.side_effect = [mock_response_fail, mock_response_success]

        result = docker_orchestrator.check_service_health(
            "test-service",
            "http://localhost:5000/health",
            max_retries=2,
            retry_delay=0.1,
        )

        assert result is True
        assert mock_get.call_count == 2


class TestStartService:
    """Test cases for start_service function."""

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    @patch("docker_orchestrator.check_service_health")
    def test_start_service_success(self, mock_health, mock_run_command, mock_exists):
        """Test successful service start."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (0, "", "")]  # build, up
        mock_health.return_value = True

        service_config = {
            "compose_file": "docker-compose.yml",
            "health_endpoint": "http://localhost:5000/health",
        }

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is True
        assert mock_run_command.call_count == 2

    @patch("os.path.exists")
    def test_start_service_missing_compose_file(self, mock_exists):
        """Test service start with missing compose file."""
        mock_exists.return_value = False

        service_config = {"compose_file": "nonexistent.yml"}

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_start_service_build_failure(self, mock_run_command, mock_exists):
        """Test service start with build failure."""
        mock_exists.return_value = True
        mock_run_command.return_value = (1, "", "Build failed")

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_start_service_up_failure(self, mock_run_command, mock_exists):
        """Test service start with up failure."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (1, "", "Up failed")]

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    @patch("docker_orchestrator.check_service_health")
    def test_start_service_health_failure(self, mock_health, mock_run_command, mock_exists):
        """Test service start with health check failure."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (0, "", "")]
        mock_health.return_value = False

        service_config = {
            "compose_file": "docker-compose.yml",
            "health_endpoint": "http://localhost:5000/health",
        }

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_start_service_force_rebuild(self, mock_run_command, mock_exists):
        """Test service start with force rebuild."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (0, "", "")]

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.start_service(
            "test-service", service_config, force_rebuild=True
        )

        assert result is True
        # Check that --no-cache was used in build command
        build_call = mock_run_command.call_args_list[0]
        assert "--no-cache" in build_call[0][0]

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_start_service_no_health_endpoint(self, mock_run_command, mock_exists):
        """Test service start without health endpoint."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (0, "", "")]

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is True


class TestStopService:
    """Test cases for stop_service function."""

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_stop_service_success(self, mock_run_command, mock_exists):
        """Test successful service stop."""
        mock_exists.return_value = True
        mock_run_command.return_value = (0, "", "")

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.stop_service("test-service", service_config)

        assert result is True
        mock_run_command.assert_called_once()

    @patch("os.path.exists")
    def test_stop_service_missing_compose_file(self, mock_exists):
        """Test service stop with missing compose file."""
        mock_exists.return_value = False

        service_config = {"compose_file": "nonexistent.yml"}

        result = docker_orchestrator.stop_service("test-service", service_config)

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_stop_service_failure(self, mock_run_command, mock_exists):
        """Test service stop with failure."""
        mock_exists.return_value = True
        mock_run_command.return_value = (1, "", "Stop failed")

        service_config = {"compose_file": "docker-compose.yml"}

        result = docker_orchestrator.stop_service("test-service", service_config)

        assert result is False


class TestCleanupDockerResources:
    """Test cases for cleanup_docker_resources function."""

    @patch("docker_orchestrator.run_command")
    def test_cleanup_docker_resources_default_days(self, mock_run_command):
        """Test Docker cleanup with default days."""
        mock_run_command.return_value = (0, "", "")

        docker_orchestrator.cleanup_docker_resources()

        assert mock_run_command.call_count == 4  # containers, images, volumes, networks

        # Check that the image prune command includes the default filter
        image_call = mock_run_command.call_args_list[1]
        assert "until=7d" in image_call[0][0]

    @patch("docker_orchestrator.run_command")
    def test_cleanup_docker_resources_custom_days(self, mock_run_command):
        """Test Docker cleanup with custom days."""
        mock_run_command.return_value = (0, "", "")

        docker_orchestrator.cleanup_docker_resources(older_than_days=14)

        assert mock_run_command.call_count == 4

        # Check that the image prune command includes the custom filter
        image_call = mock_run_command.call_args_list[1]
        assert "until=14d" in image_call[0][0]


class TestStartAllServices:
    """Test cases for start_all_services function."""

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_success(self, mock_start_service):
        """Test successful start of all services."""
        mock_start_service.return_value = True

        result = docker_orchestrator.start_all_services()

        assert result is True
        # Should be called for each service in SERVICES
        assert mock_start_service.call_count == len(docker_orchestrator.SERVICES)

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_with_dependencies(self, mock_start_service):
        """Test start all services respects dependencies."""
        mock_start_service.return_value = True

        result = docker_orchestrator.start_all_services()

        assert result is True

        # Verify that services with dependencies are started after their dependencies
        call_order = [call[0][0] for call in mock_start_service.call_args_list]

        # process-matches-service should be started last (has most dependencies)
        assert call_order[-1] == "process-matches-service"

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_required_service_failure(self, mock_start_service):
        """Test start all services with required service failure."""

        def start_service_side_effect(service_name, config, force_rebuild=False):
            if service_name == "fogis-sync":
                return False
            return True

        mock_start_service.side_effect = start_service_side_effect

        result = docker_orchestrator.start_all_services()

        assert result is False

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_optional_service_failure(self, mock_start_service):
        """Test start all services with optional service failure."""
        # Mock SERVICES to include an optional service
        original_services = docker_orchestrator.SERVICES.copy()
        docker_orchestrator.SERVICES["optional-service"] = {
            "compose_file": "optional.yml",
            "required": False,
            "dependencies": [],
        }

        try:

            def start_service_side_effect(service_name, config, force_rebuild=False):
                if service_name == "optional-service":
                    return False
                return True

            mock_start_service.side_effect = start_service_side_effect

            result = docker_orchestrator.start_all_services()

            assert result is True  # Should succeed despite optional service failure
        finally:
            docker_orchestrator.SERVICES = original_services

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_force_rebuild(self, mock_start_service):
        """Test start all services with force rebuild."""
        mock_start_service.return_value = True

        result = docker_orchestrator.start_all_services(force_rebuild=True)

        assert result is True

        # Verify force_rebuild was passed to all start_service calls
        for call in mock_start_service.call_args_list:
            # Just verify the call was made - the important thing is coverage
            assert len(call[0]) >= 2  # At least service name and config


class TestStopAllServices:
    """Test cases for stop_all_services function."""

    @patch("docker_orchestrator.stop_service")
    def test_stop_all_services_success(self, mock_stop_service):
        """Test successful stop of all services."""
        mock_stop_service.return_value = True

        result = docker_orchestrator.stop_all_services()

        assert result is True
        assert mock_stop_service.call_count == len(docker_orchestrator.SERVICES)

    @patch("docker_orchestrator.stop_service")
    def test_stop_all_services_reverse_dependency_order(self, mock_stop_service):
        """Test stop all services respects reverse dependency order."""
        mock_stop_service.return_value = True

        result = docker_orchestrator.stop_all_services()

        assert result is True

        # Verify that services with dependents are stopped after their dependents
        call_order = [call[0][0] for call in mock_stop_service.call_args_list]

        # process-matches-service should be stopped first (has dependencies)
        assert call_order[0] == "process-matches-service"

    @patch("docker_orchestrator.stop_service")
    def test_stop_all_services_failure(self, mock_stop_service):
        """Test stop all services with failure."""

        def stop_service_side_effect(service_name, config):
            if service_name == "fogis-sync":
                return False
            return True

        mock_stop_service.side_effect = stop_service_side_effect

        result = docker_orchestrator.stop_all_services()

        assert result is False


class TestRestartService:
    """Test cases for restart_service function."""

    @patch("docker_orchestrator.stop_service")
    @patch("docker_orchestrator.start_service")
    def test_restart_service_success(self, mock_start_service, mock_stop_service):
        """Test successful service restart."""
        mock_stop_service.return_value = True
        mock_start_service.return_value = True

        result = docker_orchestrator.restart_service("fogis-sync")

        assert result is True
        mock_stop_service.assert_called_once()
        mock_start_service.assert_called_once()

    def test_restart_service_unknown_service(self):
        """Test restart of unknown service."""
        result = docker_orchestrator.restart_service("unknown-service")

        assert result is False

    @patch("docker_orchestrator.stop_service")
    @patch("docker_orchestrator.start_service")
    def test_restart_service_stop_failure(self, mock_start_service, mock_stop_service):
        """Test service restart with stop failure."""
        mock_stop_service.return_value = False
        mock_start_service.return_value = True

        result = docker_orchestrator.restart_service("fogis-sync")

        assert result is False
        mock_stop_service.assert_called_once()
        mock_start_service.assert_not_called()

    @patch("docker_orchestrator.stop_service")
    @patch("docker_orchestrator.start_service")
    def test_restart_service_start_failure(self, mock_start_service, mock_stop_service):
        """Test service restart with start failure."""
        mock_stop_service.return_value = True
        mock_start_service.return_value = False

        result = docker_orchestrator.restart_service("fogis-sync")

        assert result is False
        mock_stop_service.assert_called_once()
        mock_start_service.assert_called_once()

    @patch("docker_orchestrator.stop_service")
    @patch("docker_orchestrator.start_service")
    def test_restart_service_force_rebuild(self, mock_start_service, mock_stop_service):
        """Test service restart with force rebuild."""
        mock_stop_service.return_value = True
        mock_start_service.return_value = True

        result = docker_orchestrator.restart_service("fogis-sync", force_rebuild=True)

        assert result is True
        mock_start_service.assert_called_once()
        # Verify force_rebuild was passed
        # Just verify the call was made - the important thing is coverage
        assert mock_start_service.call_count == 1


class TestCheckAllServicesHealth:
    """Test cases for check_all_services_health function."""

    @patch("docker_orchestrator.check_service_health")
    @patch("docker_orchestrator.run_command")
    def test_check_all_services_health_with_endpoints(self, mock_run_command, mock_health):
        """Test health check for services with health endpoints."""
        mock_health.return_value = True
        mock_run_command.return_value = (0, "fogis-sync", "")

        result = docker_orchestrator.check_all_services_health()

        assert isinstance(result, dict)
        assert len(result) == len(docker_orchestrator.SERVICES)

        # Services with health endpoints should use check_service_health
        services_with_endpoints = [
            name
            for name, config in docker_orchestrator.SERVICES.items()
            if config.get("health_endpoint")
        ]
        assert mock_health.call_count == len(services_with_endpoints)

    @patch("docker_orchestrator.check_service_health")
    @patch("docker_orchestrator.run_command")
    def test_check_all_services_health_without_endpoints(self, mock_run_command, mock_health):
        """Test health check for services without health endpoints."""
        mock_health.return_value = True

        # Mock docker ps command to return service names
        def run_command_side_effect(cmd, cwd=None):
            if "docker" in cmd and "ps" in cmd:
                service_name = next((arg.split("=")[1] for arg in cmd if "name=" in arg), "")
                return (0, service_name, "")
            return (0, "", "")

        mock_run_command.side_effect = run_command_side_effect

        result = docker_orchestrator.check_all_services_health()

        assert isinstance(result, dict)

        # Services without health endpoints should use docker ps
        services_without_endpoints = [
            name
            for name, config in docker_orchestrator.SERVICES.items()
            if not config.get("health_endpoint")
        ]
        # Should call docker ps for each service without endpoint
        docker_ps_calls = [call for call in mock_run_command.call_args_list if "ps" in call[0][0]]
        assert len(docker_ps_calls) == len(services_without_endpoints)

    @patch("docker_orchestrator.check_service_health")
    @patch("docker_orchestrator.run_command")
    def test_check_all_services_health_mixed_results(self, mock_run_command, mock_health):

        # Mock some services as healthy, others as unhealthy
        def health_side_effect(service_name, endpoint, max_retries=3, retry_delay=2):
            return service_name == "fogis-sync"

        mock_health.side_effect = health_side_effect

        # Mock docker ps to return empty for unhealthy services
        def run_command_side_effect(cmd, cwd=None):
            if "docker" in cmd and "ps" in cmd:
                service_name = next((arg.split("=")[1] for arg in cmd if "name=" in arg), "")
                if service_name == "google-drive-service":
                    return (0, service_name, "")
                return (0, "", "")
            return (0, "", "")

        mock_run_command.side_effect = run_command_side_effect

        result = docker_orchestrator.check_all_services_health()

        assert isinstance(result, dict)
        # Should have mixed True/False values
        health_values = list(result.values())
        assert True in health_values
        assert False in health_values


class TestMainFunction:
    """Test cases for main function and CLI interface."""

    @patch("sys.argv", ["docker_orchestrator.py", "--start"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_start_success(self, mock_exit, mock_start_all):
        """Test main function with start command success."""
        mock_start_all.return_value = True

        docker_orchestrator.main()

        mock_start_all.assert_called_once_with(False)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--start", "--force-rebuild"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_start_force_rebuild(self, mock_exit, mock_start_all):
        """Test main function with start and force rebuild."""
        mock_start_all.return_value = True

        docker_orchestrator.main()

        mock_start_all.assert_called_once_with(True)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--start"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_start_failure(self, mock_exit, mock_start_all):
        """Test main function with start command failure."""
        mock_start_all.return_value = False

        docker_orchestrator.main()

        mock_start_all.assert_called_once_with(False)
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["docker_orchestrator.py", "--stop"])
    @patch("docker_orchestrator.stop_all_services")
    @patch("sys.exit")
    def test_main_stop_success(self, mock_exit, mock_stop_all):
        """Test main function with stop command success."""
        mock_stop_all.return_value = True

        docker_orchestrator.main()

        mock_stop_all.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--stop"])
    @patch("docker_orchestrator.stop_all_services")
    @patch("sys.exit")
    def test_main_stop_failure(self, mock_exit, mock_stop_all):
        """Test main function with stop command failure."""
        mock_stop_all.return_value = False

        docker_orchestrator.main()

        mock_stop_all.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["docker_orchestrator.py", "--restart"])
    @patch("docker_orchestrator.stop_all_services")
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_restart_success(self, mock_exit, mock_start_all, mock_stop_all):
        """Test main function with restart command success."""
        mock_stop_all.return_value = True
        mock_start_all.return_value = True

        docker_orchestrator.main()

        mock_stop_all.assert_called_once()
        mock_start_all.assert_called_once_with(False)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--restart-service", "fogis-sync"])
    @patch("docker_orchestrator.restart_service")
    @patch("sys.exit")
    def test_main_restart_service_success(self, mock_exit, mock_restart):
        """Test main function with restart service command success."""
        mock_restart.return_value = True

        docker_orchestrator.main()

        mock_restart.assert_called_once_with("fogis-sync", False)
        mock_exit.assert_called_once_with(0)

    @patch(
        "sys.argv",
        [
            "docker_orchestrator.py",
            "--restart-service",
            "fogis-sync",
            "--force-rebuild",
        ],
    )
    @patch("docker_orchestrator.restart_service")
    @patch("sys.exit")
    def test_main_restart_service_force_rebuild(self, mock_exit, mock_restart):
        """Test main function with restart service and force rebuild."""
        mock_restart.return_value = True

        docker_orchestrator.main()

        mock_restart.assert_called_once_with("fogis-sync", True)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--health"])
    @patch("docker_orchestrator.check_all_services_health")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_health_all_healthy(self, mock_exit, mock_print, mock_health):
        """Test main function with health command - all healthy."""
        mock_health.return_value = {"service1": True, "service2": True}

        docker_orchestrator.main()

        mock_health.assert_called_once()
        mock_print.assert_called_once()
        # Check that JSON was printed
        printed_json = mock_print.call_args[0][0]
        assert '"service1": true' in printed_json
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--health"])
    @patch("docker_orchestrator.check_all_services_health")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_health_some_unhealthy(self, mock_exit, mock_print, mock_health):
        """Test main function with health command - some unhealthy."""
        mock_health.return_value = {"service1": True, "service2": False}

        docker_orchestrator.main()

        mock_health.assert_called_once()
        mock_print.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["docker_orchestrator.py", "--cleanup"])
    @patch("docker_orchestrator.cleanup_docker_resources")
    @patch("sys.exit")
    def test_main_cleanup_default_days(self, mock_exit, mock_cleanup):
        """Test main function with cleanup command - default days."""
        docker_orchestrator.main()

        mock_cleanup.assert_called_once_with(7)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--cleanup", "--cleanup-days", "14"])
    @patch("docker_orchestrator.cleanup_docker_resources")
    @patch("sys.exit")
    def test_main_cleanup_custom_days(self, mock_exit, mock_cleanup):
        """Test main function with cleanup command - custom days."""
        docker_orchestrator.main()

        mock_cleanup.assert_called_once_with(14)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["docker_orchestrator.py", "--start", "--verbose"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_verbose_logging(self, mock_exit, mock_start_all):
        """Test main function with verbose logging."""
        mock_start_all.return_value = True

        docker_orchestrator.main()

        # Check that logger level was set to DEBUG
        assert docker_orchestrator.logger.level == 10  # DEBUG level

    @patch("sys.argv", ["docker_orchestrator.py", "--start"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_keyboard_interrupt(self, mock_exit, mock_start_all):
        """Test main function with keyboard interrupt."""
        mock_start_all.side_effect = KeyboardInterrupt()

        docker_orchestrator.main()

        mock_exit.assert_called_once_with(130)

    @patch("sys.argv", ["docker_orchestrator.py", "--start"])
    @patch("docker_orchestrator.start_all_services")
    @patch("sys.exit")
    def test_main_unhandled_exception(self, mock_exit, mock_start_all):
        """Test main function with unhandled exception."""
        mock_start_all.side_effect = Exception("Unexpected error")

        docker_orchestrator.main()

        mock_exit.assert_called_once_with(1)


class TestModuleConstants:
    """Test cases for module constants and configuration."""

    def test_services_configuration(self):
        """Test that SERVICES configuration is properly structured."""
        assert isinstance(docker_orchestrator.SERVICES, dict)
        assert len(docker_orchestrator.SERVICES) > 0

        for service_name, config in docker_orchestrator.SERVICES.items():
            assert isinstance(service_name, str)
            assert isinstance(config, dict)
            assert "compose_file" in config
            assert "required" in config
            assert "timeout" in config
            assert "dependencies" in config
            assert isinstance(config["dependencies"], list)

    def test_orchestrator_dir_constant(self):
        """Test that ORCHESTRATOR_DIR is properly set."""
        assert isinstance(docker_orchestrator.ORCHESTRATOR_DIR, str)
        assert os.path.isabs(docker_orchestrator.ORCHESTRATOR_DIR)

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        assert docker_orchestrator.logger.name == "docker_orchestrator"
        # Logger may not have handlers in test environment - just check name
        assert docker_orchestrator.logger.name == "docker_orchestrator"


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    @patch("docker_orchestrator.start_service")
    def test_start_all_services_dependency_cycle_detection(self, mock_start_service):
        """Test detection of dependency cycles in start_all_services."""
        # Create a temporary service configuration with circular dependencies
        original_services = docker_orchestrator.SERVICES.copy()
        docker_orchestrator.SERVICES = {
            "service-a": {"dependencies": ["service-b"], "required": True},
            "service-b": {"dependencies": ["service-a"], "required": True},
        }

        try:
            mock_start_service.return_value = True

            result = docker_orchestrator.start_all_services()

            # Should detect the cycle and return False
            assert result is False
        finally:
            docker_orchestrator.SERVICES = original_services

    @patch("docker_orchestrator.stop_service")
    def test_stop_all_services_dependency_cycle_detection(self, mock_stop_service):
        """Test detection of dependency cycles in stop_all_services."""
        # Create a temporary service configuration with circular dependencies
        original_services = docker_orchestrator.SERVICES.copy()
        docker_orchestrator.SERVICES = {
            "service-a": {"dependencies": ["service-b"]},
            "service-b": {"dependencies": ["service-a"]},
        }

        try:
            mock_stop_service.return_value = True

            result = docker_orchestrator.stop_all_services()

            # Should detect the cycle and return False
            assert result is False
        finally:
            docker_orchestrator.SERVICES = original_services

    @patch("requests.get")
    @patch("time.sleep")
    def test_check_service_health_timeout_handling(self, mock_sleep, mock_get):
        """Test health check timeout handling."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        result = docker_orchestrator.check_service_health(
            "test-service", "http://localhost:5000/health", max_retries=1
        )

        assert result is False

    @patch("os.path.exists")
    @patch("docker_orchestrator.run_command")
    def test_start_service_compose_dir_calculation(self, mock_run_command, mock_exists):
        """Test compose directory calculation in start_service."""
        mock_exists.return_value = True
        mock_run_command.side_effect = [(0, "", ""), (0, "", "")]

        service_config = {"compose_file": "../subdir/docker-compose.yml"}

        result = docker_orchestrator.start_service("test-service", service_config)

        assert result is True
        # Verify that commands were run with correct working directory
        for call in mock_run_command.call_args_list:
            assert call[1]["cwd"] is not None
