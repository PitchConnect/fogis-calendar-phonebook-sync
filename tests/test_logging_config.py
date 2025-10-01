"""Tests for logging configuration module."""

import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.core.logging_config import (
    CalendarSyncServiceFormatter,
    configure_logging,
    get_logger,
    log_error_context,
)


class TestCalendarSyncServiceFormatter:
    """Tests for CalendarSyncServiceFormatter class."""

    def test_format_basic_message(self):
        """Test formatting a basic log message."""
        formatter = CalendarSyncServiceFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        result = formatter.format(record)

        assert "fogis-calendar-phonebook-sync" in result
        assert "INFO" in result
        assert "Test message" in result
        assert "test.py:test_function:42" in result

    def test_format_with_exception(self):
        """Test formatting a log message with exception."""
        formatter = CalendarSyncServiceFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.funcName = "test_function"

        result = formatter.format(record)

        assert "ERROR" in result
        assert "Error occurred" in result
        assert "[Error: ValueError]" in result

    def test_filter_sensitive_data_access_token(self):
        """Test filtering of access tokens."""
        formatter = CalendarSyncServiceFormatter()
        message = 'Response: {"access_token": "secret123456", "data": "public"}'

        result = formatter._filter_sensitive_data(message)

        assert "secret123456" not in result
        assert "[FILTERED]" in result
        assert "public" in result

    def test_filter_sensitive_data_refresh_token(self):
        """Test filtering of refresh tokens."""
        formatter = CalendarSyncServiceFormatter()
        message = 'Config: {"refresh_token": "refresh_secret", "timeout": 30}'

        result = formatter._filter_sensitive_data(message)

        assert "refresh_secret" not in result
        assert "[FILTERED]" in result

    def test_filter_sensitive_data_bearer_token(self):
        """Test filtering of Bearer tokens."""
        formatter = CalendarSyncServiceFormatter()
        message = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

        result = formatter._filter_sensitive_data(message)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer [FILTERED]" in result

    def test_filter_sensitive_data_password(self):
        """Test filtering of passwords."""
        formatter = CalendarSyncServiceFormatter()
        message = "Login with password: mySecretPass123"

        result = formatter._filter_sensitive_data(message)

        assert "mySecretPass123" not in result
        assert "[FILTERED]" in result

    def test_filter_sensitive_data_fogis_credentials(self):
        """Test filtering of FOGIS credentials."""
        formatter = CalendarSyncServiceFormatter()
        message = "FOGIS_USERNAME: user123, FOGIS_PASSWORD: pass456"

        result = formatter._filter_sensitive_data(message)

        assert "user123" not in result
        assert "pass456" not in result
        assert "[FILTERED]" in result

    def test_filter_sensitive_data_email(self):
        """Test filtering of email addresses."""
        formatter = CalendarSyncServiceFormatter()
        message = "User email: test@example.com sent notification"

        result = formatter._filter_sensitive_data(message)

        assert "test@example.com" not in result
        assert "[EMAIL_FILTERED]" in result

    def test_extract_component_from_logger_name(self):
        """Test component extraction from logger name."""
        formatter = CalendarSyncServiceFormatter()
        record = logging.LogRecord(
            name="fogis.calendar.sync",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        component = formatter._extract_component(record)

        assert component == "sync"

    def test_extract_component_from_pathname(self):
        """Test component extraction from pathname."""
        formatter = CalendarSyncServiceFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/calendar_sync.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        component = formatter._extract_component(record)

        assert component == "calendar_sync"

    def test_extract_component_default(self):
        """Test default component extraction."""
        formatter = CalendarSyncServiceFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )

        component = formatter._extract_component(record)

        assert component == "core"


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_basic(self):
        """Test getting a basic logger."""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_with_component(self):
        """Test getting a logger with component context."""
        logger = get_logger("test.module", component="test_component")

        assert isinstance(logger, logging.LoggerAdapter)
        assert logger.extra["component"] == "test_component"


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_default(self):
        """Test logging configuration with default settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(log_dir=temp_dir)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO
            assert len(root_logger.handlers) >= 1

    def test_configure_logging_debug_level(self):
        """Test logging configuration with DEBUG level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(log_level="DEBUG", log_dir=temp_dir)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_configure_logging_console_only(self):
        """Test logging configuration with console only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(enable_console=True, enable_file=False, log_dir=temp_dir)

            root_logger = logging.getLogger()
            assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)

    def test_configure_logging_file_only(self):
        """Test logging configuration with file only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(enable_console=False, enable_file=True, log_dir=temp_dir)

            root_logger = logging.getLogger()
            assert any(
                isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers
            )

    def test_configure_logging_creates_log_directory(self):
        """Test that logging configuration creates log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "new_logs")
            configure_logging(log_dir=log_dir)

            assert os.path.exists(log_dir)

    def test_configure_logging_unstructured(self):
        """Test logging configuration with unstructured format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_logging(enable_structured=False, log_dir=temp_dir)

            root_logger = logging.getLogger()
            # Check that handlers exist
            assert len(root_logger.handlers) >= 1


class TestLogErrorContext:
    """Tests for log_error_context function."""

    def test_log_error_context_basic(self):
        """Test logging error with basic context."""
        logger = MagicMock()
        error = ValueError("Test error")

        log_error_context(logger, error, operation="test_operation")

        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "test_operation" in call_args[0][0]
        assert "Test error" in call_args[0][0]

    def test_log_error_context_with_context(self):
        """Test logging error with additional context."""
        logger = MagicMock()
        error = ValueError("Test error")
        context = {"user_id": "123", "action": "sync"}

        log_error_context(logger, error, context=context, operation="sync_calendar")

        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[1]["exc_info"] is True

    def test_log_error_context_filters_sensitive_data(self):
        """Test that error context filters sensitive data."""
        logger = MagicMock()
        error = ValueError("Test error")
        context = {"password": "secret123", "username": "user"}

        log_error_context(logger, error, context=context, operation="login")

        logger.error.assert_called_once()
        # The password should be filtered in the context
        call_args = logger.error.call_args
        error_context = call_args[1]["extra"]["error_context"]
        assert error_context["context"]["password"] == "[FILTERED]"
        assert "user" in str(error_context["context"]["username"])

    def test_log_error_context_truncates_long_values(self):
        """Test that error context truncates long values."""
        logger = MagicMock()
        error = ValueError("Test error")
        long_value = "x" * 300
        context = {"data": long_value}

        log_error_context(logger, error, context=context, operation="process")

        logger.error.assert_called_once()
        call_args = logger.error.call_args
        error_context = call_args[1]["extra"]["error_context"]
        # Value should be truncated to 200 characters
        assert len(error_context["context"]["data"]) == 200
