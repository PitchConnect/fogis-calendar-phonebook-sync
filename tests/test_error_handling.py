"""Tests for error handling module."""

import pytest

from src.core.error_handling import (
    AuthenticationError,
    CalendarAPIError,
    CalendarSyncError,
    ConfigurationError,
    ContactsAPIError,
    FogisAPIError,
    handle_calendar_errors,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_calendar_sync_error(self):
        """Test CalendarSyncError can be raised and caught."""
        with pytest.raises(CalendarSyncError):
            raise CalendarSyncError("Test error")

    def test_authentication_error(self):
        """Test AuthenticationError can be raised and caught."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth failed")

    def test_authentication_error_is_calendar_sync_error(self):
        """Test AuthenticationError is a subclass of CalendarSyncError."""
        assert issubclass(AuthenticationError, CalendarSyncError)

    def test_calendar_api_error(self):
        """Test CalendarAPIError can be raised and caught."""
        with pytest.raises(CalendarAPIError):
            raise CalendarAPIError("Calendar API failed")

    def test_calendar_api_error_is_calendar_sync_error(self):
        """Test CalendarAPIError is a subclass of CalendarSyncError."""
        assert issubclass(CalendarAPIError, CalendarSyncError)

    def test_contacts_api_error(self):
        """Test ContactsAPIError can be raised and caught."""
        with pytest.raises(ContactsAPIError):
            raise ContactsAPIError("Contacts API failed")

    def test_contacts_api_error_is_calendar_sync_error(self):
        """Test ContactsAPIError is a subclass of CalendarSyncError."""
        assert issubclass(ContactsAPIError, CalendarSyncError)

    def test_fogis_api_error(self):
        """Test FogisAPIError can be raised and caught."""
        with pytest.raises(FogisAPIError):
            raise FogisAPIError("FOGIS API failed")

    def test_fogis_api_error_is_calendar_sync_error(self):
        """Test FogisAPIError is a subclass of CalendarSyncError."""
        assert issubclass(FogisAPIError, CalendarSyncError)

    def test_configuration_error(self):
        """Test ConfigurationError can be raised and caught."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config invalid")

    def test_configuration_error_is_calendar_sync_error(self):
        """Test ConfigurationError is a subclass of CalendarSyncError."""
        assert issubclass(ConfigurationError, CalendarSyncError)


class TestHandleCalendarErrors:
    """Tests for handle_calendar_errors decorator."""

    def test_decorator_successful_execution(self):
        """Test decorator allows successful function execution."""

        @handle_calendar_errors("test_operation")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_decorator_with_arguments(self):
        """Test decorator works with functions that have arguments."""

        @handle_calendar_errors("test_operation")
        def function_with_args(a, b):
            return a + b

        result = function_with_args(2, 3)
        assert result == 5

    def test_decorator_with_kwargs(self):
        """Test decorator works with keyword arguments."""

        @handle_calendar_errors("test_operation")
        def function_with_kwargs(a, b=10):
            return a + b

        result = function_with_kwargs(5, b=15)
        assert result == 20

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves the original function name."""

        @handle_calendar_errors("test_operation")
        def my_function():
            return "test"

        assert my_function.__name__ == "my_function"

    def test_decorator_with_authentication_error(self):
        """Test decorator handles AuthenticationError."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_auth():
            raise AuthenticationError("Auth failed")

        with pytest.raises(AuthenticationError):
            function_that_fails_auth()

    def test_decorator_with_calendar_api_error(self):
        """Test decorator handles CalendarAPIError."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_calendar():
            raise CalendarAPIError("Calendar API failed")

        with pytest.raises(CalendarAPIError):
            function_that_fails_calendar()

    def test_decorator_with_contacts_api_error(self):
        """Test decorator handles ContactsAPIError."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_contacts():
            raise ContactsAPIError("Contacts API failed")

        with pytest.raises(ContactsAPIError):
            function_that_fails_contacts()

    def test_decorator_with_fogis_api_error(self):
        """Test decorator handles FogisAPIError."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_fogis():
            raise FogisAPIError("FOGIS API failed")

        with pytest.raises(FogisAPIError):
            function_that_fails_fogis()

    def test_decorator_with_configuration_error(self):
        """Test decorator handles ConfigurationError."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_config():
            raise ConfigurationError("Config invalid")

        with pytest.raises(ConfigurationError):
            function_that_fails_config()

    def test_decorator_with_generic_exception(self):
        """Test decorator handles generic exceptions."""

        @handle_calendar_errors("test_operation")
        def function_that_fails_generic():
            raise ValueError("Generic error")

        with pytest.raises(ValueError):
            function_that_fails_generic()

    def test_decorator_with_custom_component(self):
        """Test decorator with custom component name."""

        @handle_calendar_errors("test_operation", component="custom_component")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"
