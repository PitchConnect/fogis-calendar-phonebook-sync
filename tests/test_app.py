"""Tests for the app module."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.app.config["TESTING"] = True
    with app.app.test_client() as test_client:
        yield test_client


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_success(client):
    """Test the sync endpoint with a successful sync."""
    # Mock the subprocess.run function
    with patch("subprocess.run") as mock_run:
        # Configure the mock for success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed successfully"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Mock the environment variables
        with patch.dict("os.environ", {"PYTHONPATH": "/app"}):
            # Call the endpoint
            response = client.post("/sync")

            # Verify the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["message"] == "FOGIS sync completed successfully"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_failure(client):
    """Test the sync endpoint with a failed sync."""
    # Mock the subprocess.run function
    with patch("subprocess.run") as mock_run:
        # Configure the mock for failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Error during sync"
        mock_run.return_value = mock_process

        # Mock the environment variables
        with patch.dict("os.environ", {"PYTHONPATH": "/app"}):
            # Call the endpoint
            response = client.post("/sync")

            # Verify the response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["status"] == "error"
            assert data["message"] == "FOGIS sync failed"
            assert data["error"] == "Error during sync"
