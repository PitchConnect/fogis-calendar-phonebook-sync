"""Tests for version module."""

import os
from unittest.mock import patch

import pytest

import version


class TestVersionModule:
    """Test cases for the version module."""

    @pytest.mark.unit
    def test_version_default_value(self):
        """Test that VERSION has a default value when no environment variable is set."""
        with patch.dict("os.environ", {}, clear=True):
            # Re-import to get fresh environment
            import importlib

            importlib.reload(version)

            # Should default to "dev"
            assert version.VERSION == "dev"

    @pytest.mark.unit
    def test_version_from_environment(self):
        """Test that VERSION is read from environment variable."""
        test_version = "1.2.3"
        with patch.dict("os.environ", {"VERSION": test_version}):
            # Re-import to get fresh environment
            import importlib

            importlib.reload(version)

            assert version.VERSION == test_version

    @pytest.mark.unit
    def test_version_empty_string_from_environment(self):
        """Test that empty string VERSION from environment is preserved."""
        with patch.dict("os.environ", {"VERSION": ""}):
            # Re-import to get fresh environment
            import importlib

            importlib.reload(version)

            assert version.VERSION == ""

    @pytest.mark.unit
    def test_get_version_function(self):
        """Test the get_version function returns the VERSION constant."""
        # Test with current VERSION value
        result = version.get_version()
        assert result == version.VERSION

    @pytest.mark.unit
    def test_get_version_function_with_custom_version(self):
        """Test get_version function with a custom version."""
        test_version = "2.0.0-beta"
        with patch.dict("os.environ", {"VERSION": test_version}):
            # Re-import to get fresh environment
            import importlib

            importlib.reload(version)

            result = version.get_version()
            assert result == test_version
            assert result == version.VERSION

    @pytest.mark.unit
    def test_get_version_function_consistency(self):
        """Test that get_version always returns the same value as VERSION."""
        # Test multiple calls return consistent results
        result1 = version.get_version()
        result2 = version.get_version()

        assert result1 == result2
        assert result1 == version.VERSION

    @pytest.mark.unit
    def test_version_module_attributes(self):
        """Test that the version module has expected attributes."""
        # Check that VERSION attribute exists
        assert hasattr(version, "VERSION")

        # Check that get_version function exists
        assert hasattr(version, "get_version")
        assert callable(version.get_version)

    @pytest.mark.unit
    def test_version_types(self):
        """Test that version values have correct types."""
        # VERSION should be a string
        assert isinstance(version.VERSION, str)

        # get_version() should return a string
        result = version.get_version()
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_version_with_special_characters(self):
        """Test version with special characters and formats."""
        special_versions = [
            "1.0.0-alpha.1",
            "2.0.0+build.123",
            "1.0.0-rc.1+build.456",
            "v1.2.3",
            "release-2023.01.15",
        ]

        for test_version in special_versions:
            with patch.dict("os.environ", {"VERSION": test_version}):
                # Re-import to get fresh environment
                import importlib

                importlib.reload(version)

                assert version.VERSION == test_version
                assert version.get_version() == test_version

    @pytest.mark.unit
    def test_version_docstring(self):
        """Test that the get_version function has proper documentation."""
        # Check that function has a docstring
        assert version.get_version.__doc__ is not None
        assert len(version.get_version.__doc__.strip()) > 0

        # Check that module has a docstring
        assert version.__doc__ is not None
        assert "Version information" in version.__doc__
