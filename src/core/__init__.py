"""
Core modules for FOGIS Calendar & Phonebook Sync service.

This package contains the enhanced logging and error handling infrastructure
following the v2.1.0 standard.
"""

from .error_handling import (
    AuthenticationError,
    CalendarAPIError,
    CalendarSyncError,
    CircuitBreaker,
    ConfigurationError,
    ContactsAPIError,
    FogisAPIError,
    create_error_context,
    handle_api_errors,
    handle_calendar_errors,
    log_error_context,
    safe_execute,
    validate_configuration,
)
from .logging_config import configure_logging, get_logger

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    # Error handling
    "CalendarSyncError",
    "AuthenticationError",
    "CalendarAPIError",
    "ContactsAPIError",
    "FogisAPIError",
    "ConfigurationError",
    "handle_calendar_errors",
    "handle_api_errors",
    "log_error_context",
    "CircuitBreaker",
    "safe_execute",
    "validate_configuration",
    "create_error_context",
]
