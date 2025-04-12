#!/bin/bash
# Simple wrapper script for docker_orchestrator.py

# Make sure the script is executable
chmod +x docker_orchestrator.py

# Pass all arguments to the Python script
./docker_orchestrator.py "$@"
