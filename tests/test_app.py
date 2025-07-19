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
    # Mock os.path.exists to return True for the data directory check
    # Mock get_version to return a test version
    with patch("os.path.exists", return_value=True), patch(
        "app.get_version", return_value="test-version"
    ):
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "test-version"
        assert "environment" in data


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


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_no_data_directory(client):
    """Test health check when data directory doesn't exist."""
    with patch("os.path.exists", return_value=False):
        response = client.get("/health")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Data directory not accessible" in data["message"]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_no_token_file(client):
    """Test health check when OAuth token doesn't exist in any location."""
    with patch("os.path.exists") as mock_exists:
        # First call (data directory) returns True, then all token locations return False
        mock_exists.side_effect = [True, False, False, False]

        with patch("app.get_version", return_value="test-version"):
            response = client.get("/health")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "warning"
            assert "OAuth token not found" in data["message"]
            assert "checked_locations" in data


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_exception(client):
    """Test health check when an exception occurs."""
    with patch("app.get_version", side_effect=Exception("Version error")):
        response = client.get("/health")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_with_credentials(client):
    """Test sync endpoint with FOGIS credentials."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        response = client.post(
            "/sync", json={"username": "test_user", "password": "test_pass", "delete": False}
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

        # Verify subprocess was called with correct environment
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "FOGIS_USERNAME" in call_args.kwargs["env"]
        assert "FOGIS_PASSWORD" in call_args.kwargs["env"]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_with_delete_flag(client):
    """Test sync endpoint with delete flag."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        response = client.post("/sync", json={"delete": True})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

        # Verify subprocess was called with --delete flag
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "--delete" in call_args[0][0]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_exception(client):
    """Test sync endpoint when an exception occurs."""
    with patch("subprocess.run", side_effect=Exception("Subprocess error")):
        response = client.post("/sync")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Error during FOGIS sync" in data["message"]
