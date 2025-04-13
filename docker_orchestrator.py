#!/usr/bin/env python3
"""Docker Orchestration Script for Fogis Services.

This script manages the orchestration of Docker containers for the Fogis services,
including health checks, version management, and cleanup.
"""

import argparse
import json
import logging
import os
import requests
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("docker_orchestrator.log")],
)
logger = logging.getLogger(__name__)

# Configuration
SERVICES = {
    "fogis-sync": {
        "compose_file": "../FogisCalendarPhoneBookSync/docker-compose.yml",
        "health_endpoint": "http://localhost:5003/health",
        "required": True,
        "timeout": 60,
        "dependencies": [],
    },
    "fogis-api-client-service": {
        "compose_file": "../fogis_api_client_python/docker-compose.yml",
        "health_endpoint": "http://localhost:8080/hello",
        "required": True,
        "timeout": 60,
        "dependencies": [],
    },
    "google-drive-service": {
        "compose_file": "../google-drive-service/docker-compose.yml",
        "health_endpoint": None,  # No health endpoint available
        "required": True,
        "timeout": 60,
        "dependencies": [],
    },
    "whatsapp-avatar-service": {
        "compose_file": "../TeamLogoCombiner/docker-compose.yml",
        "health_endpoint": None,  # No health endpoint available
        "required": True,
        "timeout": 60,
        "dependencies": [],
    },
    "process-matches-service": {
        "compose_file": "../MatchListProcessor/docker-compose.yml",
        "health_endpoint": None,  # No health endpoint available
        "required": True,
        "timeout": 60,
        "dependencies": [
            "fogis-sync",
            "fogis-api-client-service",
            "google-drive-service",
            "whatsapp-avatar-service",
        ],
    },
}

# Main orchestrator directory
ORCHESTRATOR_DIR = os.path.dirname(os.path.abspath(__file__))


def run_command(command: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return the exit code, stdout, and stderr.

    Args:
        command: List of command and arguments
        cwd: Working directory for the command

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    logger.debug("Running command: %s", " ".join(command))

    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd
        ) as process:
            stdout, stderr = process.communicate()
            exit_code = process.returncode

        if exit_code != 0:
            logger.warning(f"Command exited with code {exit_code}: {' '.join(command)}")
            logger.warning(f"stderr: {stderr}")

        return exit_code, stdout, stderr

    except Exception as e:
        logger.error(f"Error running command {' '.join(command)}: {e}")
        return 1, "", str(e)


def check_service_health(
    service_name: str, endpoint: str, max_retries: int = 10, retry_delay: int = 5
) -> bool:
    """Check if a service is healthy by making a request to its health endpoint.

    Args:
        service_name: Name of the service
        endpoint: Health check endpoint URL
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if the service is healthy, False otherwise
    """
    if not endpoint:
        logger.warning(f"No health endpoint defined for {service_name}, assuming healthy")
        return True

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Checking health of {service_name} at {endpoint} (attempt {attempt+1}/{max_retries})"
            )
            response = requests.get(endpoint, timeout=10)

            if response.status_code == 200:
                logger.info(f"{service_name} is healthy")
                return True

            logger.warning(
                f"{service_name} health check failed with status code {response.status_code}"
            )

        except requests.RequestException as e:
            logger.warning(f"Error checking {service_name} health: {e}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    logger.error(f"{service_name} health check failed after {max_retries} attempts")
    return False


def start_service(service_name: str, service_config: Dict, force_rebuild: bool = False) -> bool:
    """Start a Docker service.

    Args:
        service_name: Name of the service
        service_config: Service configuration
        force_rebuild: Whether to force a rebuild of the service

    Returns:
        True if the service started successfully, False otherwise
    """
    compose_file = service_config["compose_file"]
    compose_dir = os.path.dirname(os.path.join(ORCHESTRATOR_DIR, compose_file))

    # Check if the compose file exists
    if not os.path.exists(os.path.join(ORCHESTRATOR_DIR, compose_file)):
        logger.error(f"Compose file not found: {compose_file}")
        return False

    # Build and start the service
    logger.info(f"Starting service: {service_name}")

    build_cmd = ["docker", "compose"]

    if force_rebuild:
        build_cmd.extend(["build", "--no-cache", service_name])
    else:
        build_cmd.extend(["build", service_name])

    exit_code, _, stderr = run_command(build_cmd, cwd=compose_dir)
    if exit_code != 0:
        logger.error(f"Failed to build {service_name}: {stderr}")
        return False

    up_cmd = ["docker", "compose", "up", "-d", service_name]
    exit_code, _, stderr = run_command(up_cmd, cwd=compose_dir)
    if exit_code != 0:
        logger.error(f"Failed to start {service_name}: {stderr}")
        return False

    # Check service health if endpoint is defined
    if service_config.get("health_endpoint"):
        return check_service_health(
            service_name,
            service_config["health_endpoint"],
            max_retries=service_config.get("max_retries", 10),
            retry_delay=service_config.get("retry_delay", 5),
        )

    return True


def stop_service(service_name: str, service_config: Dict) -> bool:
    """Stop a Docker service.

    Args:
        service_name: Name of the service
        service_config: Service configuration

    Returns:
        True if the service stopped successfully, False otherwise
    """
    compose_file = service_config["compose_file"]
    compose_dir = os.path.dirname(os.path.join(ORCHESTRATOR_DIR, compose_file))

    # Check if the compose file exists
    if not os.path.exists(os.path.join(ORCHESTRATOR_DIR, compose_file)):
        logger.error(f"Compose file not found: {compose_file}")
        return False

    # Stop the service
    logger.info(f"Stopping service: {service_name}")

    down_cmd = ["docker", "compose", "down", service_name]
    exit_code, _, stderr = run_command(down_cmd, cwd=compose_dir)
    if exit_code != 0:
        logger.error(f"Failed to stop {service_name}: {stderr}")
        return False

    return True


def cleanup_docker_resources(older_than_days: int = 7) -> None:
    """Clean up unused Docker resources.

    Args:
        older_than_days: Remove resources older than this many days
    """
    logger.info("Cleaning up Docker resources")

    # Remove unused containers
    _, _, _ = run_command(["docker", "container", "prune", "-f"])

    # Remove unused images
    _, _, _ = run_command(
        ["docker", "image", "prune", "-a", "-f", "--filter", f"until={older_than_days}d"]
    )

    # Remove unused volumes
    _, _, _ = run_command(["docker", "volume", "prune", "-f"])

    # Remove unused networks
    _, _, _ = run_command(["docker", "network", "prune", "-f"])

    logger.info("Docker cleanup completed")


def start_all_services(force_rebuild: bool = False) -> bool:
    """Start all services in the correct order based on dependencies.

    Args:
        force_rebuild: Whether to force a rebuild of all services

    Returns:
        True if all required services started successfully, False otherwise
    """
    logger.info("Starting all services")

    # Create a dependency graph
    remaining_services = list(SERVICES.keys())
    started_services = []

    # Keep track of failed services
    failed_services = []

    # Start services until all are started or we can't make progress
    while remaining_services:
        progress_made = False

        for service_name in list(remaining_services):
            service_config = SERVICES[service_name]
            dependencies = service_config.get("dependencies", [])

            # Check if all dependencies are started
            if all(dep in started_services for dep in dependencies):
                logger.info(f"Starting {service_name} (dependencies satisfied)")

                if start_service(service_name, service_config, force_rebuild):
                    started_services.append(service_name)
                    remaining_services.remove(service_name)
                    progress_made = True
                else:
                    if service_config.get("required", True):
                        failed_services.append(service_name)
                        logger.error(f"Failed to start required service: {service_name}")
                    else:
                        logger.warning(f"Failed to start optional service: {service_name}")
                    remaining_services.remove(service_name)
                    progress_made = True

        # If we couldn't make progress, there might be a dependency cycle
        if not progress_made:
            logger.error(
                f"Could not make progress starting services. Remaining: {remaining_services}"
            )
            return False

    # Check if any required services failed
    if failed_services:
        logger.error(f"Failed to start required services: {failed_services}")
        return False

    logger.info("All services started successfully")
    return True


def stop_all_services() -> bool:
    """Stop all services in reverse dependency order.

    Returns:
        True if all services stopped successfully, False otherwise
    """
    logger.info("Stopping all services")

    # Create a reverse dependency graph
    service_dependents = {service: [] for service in SERVICES}
    for service_name, config in SERVICES.items():
        for dependency in config.get("dependencies", []):
            service_dependents[dependency].append(service_name)

    # Stop services in reverse dependency order
    remaining_services = list(SERVICES.keys())
    stopped_services = []

    # Keep track of failed services
    failed_services = []

    # Stop services until all are stopped or we can't make progress
    while remaining_services:
        progress_made = False

        for service_name in list(remaining_services):
            dependents = service_dependents[service_name]

            # Check if all dependents are stopped
            if all(dep in stopped_services for dep in dependents):
                logger.info(f"Stopping {service_name} (dependents stopped)")

                if stop_service(service_name, SERVICES[service_name]):
                    stopped_services.append(service_name)
                    remaining_services.remove(service_name)
                    progress_made = True
                else:
                    failed_services.append(service_name)
                    logger.error(f"Failed to stop service: {service_name}")
                    remaining_services.remove(service_name)
                    progress_made = True

        # If we couldn't make progress, there might be a dependency cycle
        if not progress_made:
            logger.error(
                f"Could not make progress stopping services. Remaining: {remaining_services}"
            )
            return False

    # Check if any services failed to stop
    if failed_services:
        logger.error(f"Failed to stop services: {failed_services}")
        return False

    logger.info("All services stopped successfully")
    return True


def restart_service(service_name: str, force_rebuild: bool = False) -> bool:
    """Restart a specific service and its dependencies.

    Args:
        service_name: Name of the service to restart
        force_rebuild: Whether to force a rebuild of the service

    Returns:
        True if the service restarted successfully, False otherwise
    """
    if service_name not in SERVICES:
        logger.error(f"Unknown service: {service_name}")
        return False

    logger.info(f"Restarting service: {service_name}")

    # Get the service configuration
    service_config = SERVICES[service_name]

    # Stop the service
    if not stop_service(service_name, service_config):
        logger.error(f"Failed to stop {service_name}")
        return False

    # Start the service
    if not start_service(service_name, service_config, force_rebuild):
        logger.error(f"Failed to start {service_name}")
        return False

    logger.info(f"Service {service_name} restarted successfully")
    return True


def check_all_services_health() -> Dict[str, bool]:
    """Check the health of all services.

    Returns:
        Dictionary mapping service names to health status (True=healthy, False=unhealthy)
    """
    logger.info("Checking health of all services")

    health_status = {}

    for service_name, service_config in SERVICES.items():
        health_endpoint = service_config.get("health_endpoint")

        if health_endpoint:
            health_status[service_name] = check_service_health(
                service_name,
                health_endpoint,
                max_retries=service_config.get("max_retries", 3),
                retry_delay=service_config.get("retry_delay", 2),
            )
        else:
            # If no health endpoint, check if the container is running
            cmd = ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Names}}"]
            exit_code, stdout, _ = run_command(cmd)

            if exit_code == 0 and service_name in stdout:
                logger.info(f"{service_name} container is running")
                health_status[service_name] = True
            else:
                logger.warning(f"{service_name} container is not running")
                health_status[service_name] = False

    return health_status


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Docker Orchestration Script for Fogis Services")

    # Command group
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--start", action="store_true", help="Start all services")
    command_group.add_argument("--stop", action="store_true", help="Stop all services")
    command_group.add_argument("--restart", action="store_true", help="Restart all services")
    command_group.add_argument("--restart-service", type=str, help="Restart a specific service")
    command_group.add_argument("--health", action="store_true", help="Check health of all services")
    command_group.add_argument("--cleanup", action="store_true", help="Clean up Docker resources")

    # Options
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild of services")
    parser.add_argument(
        "--cleanup-days", type=int, default=7, help="Clean up resources older than this many days"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Execute the requested command
    try:
        if args.start:
            success = start_all_services(args.force_rebuild)
            sys.exit(0 if success else 1)

        elif args.stop:
            success = stop_all_services()
            sys.exit(0 if success else 1)

        elif args.restart:
            stop_all_services()
            success = start_all_services(args.force_rebuild)
            sys.exit(0 if success else 1)

        elif args.restart_service:
            success = restart_service(args.restart_service, args.force_rebuild)
            sys.exit(0 if success else 1)

        elif args.health:
            health_status = check_all_services_health()
            print(json.dumps(health_status, indent=2))
            all_healthy = all(health_status.values())
            sys.exit(0 if all_healthy else 1)

        elif args.cleanup:
            cleanup_docker_resources(args.cleanup_days)
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
