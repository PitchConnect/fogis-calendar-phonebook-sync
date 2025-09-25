"""
Enhanced logging configuration for FOGIS Calendar & Phonebook Sync service.

This module provides enterprise-grade structured logging following the v2.1.0 standard
established in the match-list-processor service. It includes service context, component
separation, location information, and comprehensive error handling.
"""

import logging
import logging.handlers
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional


class CalendarSyncServiceFormatter(logging.Formatter):
    """Enhanced formatter for FOGIS Calendar & Phonebook Sync service with structured output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with enhanced structure and context."""
        # Create structured log format
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")
        service = "fogis-calendar-phonebook-sync"

        # Extract component from logger name or record
        component = getattr(record, "component", self._extract_component(record))
        level = record.levelname

        # Create location information
        location = f"{os.path.basename(record.pathname)}:{record.lineno}"
        if hasattr(record, "funcName") and record.funcName != "<module>":
            location = f"{os.path.basename(record.pathname)}:{record.funcName}:{record.lineno}"

        # Get and filter message
        message = record.getMessage()
        message = self._filter_sensitive_data(message)

        # Add error context for exceptions
        if record.exc_info:
            error_type = record.exc_info[0].__name__ if record.exc_info[0] else "Unknown"
            message = f"{message} [Error: {error_type}]"

        return f"{timestamp} - {service} - {component} - {level} - {location} - {message}"

    def _extract_component(self, record: logging.LogRecord) -> str:
        """Extract component name from logger name or module."""
        # Use explicit component if set
        if hasattr(record, "component"):
            return record.component

        # Extract from logger name
        name_parts = record.name.split(".")
        if len(name_parts) >= 2:
            return name_parts[-1]

        # Extract from pathname
        if record.pathname:
            filename = os.path.basename(record.pathname)
            if filename.endswith(".py"):
                return filename[:-3]

        return "core"

    def _filter_sensitive_data(self, message: str) -> str:
        """Filter sensitive data from log messages."""
        # Define patterns for sensitive information
        patterns = [
            # OAuth tokens and credentials
            (r'"access_token":\s*"[^"]+', '"access_token": "[FILTERED]'),
            (r'"refresh_token":\s*"[^"]+', '"refresh_token": "[FILTERED]'),
            (r"Bearer [A-Za-z0-9._-]+", "Bearer [FILTERED]"),
            (r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9._-]{20,}', "token: [FILTERED]"),
            # Passwords and secrets
            (r'password["\']?\s*[:=]\s*["\']?[^\s"\'`,}]+', "password: [FILTERED]"),
            (r'secret["\']?\s*[:=]\s*["\']?[^\s"\'`,}]+', "secret: [FILTERED]"),
            (r'key["\']?\s*[:=]\s*["\']?[A-Za-z0-9._-]{20,}', "key: [FILTERED]"),
            # FOGIS credentials
            (
                r'FOGIS_USERNAME["\']?\s*[:=]\s*["\']?[^\s"\'`,}]+',
                "FOGIS_USERNAME: [FILTERED]",
            ),
            (
                r'FOGIS_PASSWORD["\']?\s*[:=]\s*["\']?[^\s"\'`,}]+',
                "FOGIS_PASSWORD: [FILTERED]",
            ),
            # Google API credentials
            (r'"client_id":\s*"[^"]+', '"client_id": "[FILTERED]'),
            (r'"client_secret":\s*"[^"]+', '"client_secret": "[FILTERED]'),
            # Email addresses (partial filtering)
            (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL_FILTERED]"),
        ]

        filtered_message = message
        for pattern, replacement in patterns:
            filtered_message = re.sub(pattern, replacement, filtered_message, flags=re.IGNORECASE)

        return filtered_message


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger for the FOGIS Calendar & Phonebook Sync service.

    Args:
        name: Logger name (typically __name__)
        component: Optional component name for context

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Add component context if provided
    if component:
        logger = logging.LoggerAdapter(logger, {"component": component})

    return logger


def configure_logging(
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_structured: bool = True,
    log_dir: str = "logs",
    log_file: str = "fogis-calendar-phonebook-sync.log",
) -> None:
    """
    Configure enhanced logging for FOGIS Calendar & Phonebook Sync service.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Enable console output
        enable_file: Enable file output
        enable_structured: Enable structured logging format
        log_dir: Directory for log files
        log_file: Log file name
    """
    # Create log directory if it doesn't exist
    if enable_file:
        os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Choose formatter based on structured logging setting
    if enable_structured:
        formatter = CalendarSyncServiceFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, log_file),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,  # 10MB
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce verbosity of third-party libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)

    # Log configuration success
    logger = get_logger(__name__, "logging_config")
    logger.info(
        f"Logging configured: level={log_level}, console={enable_console}, "
        f"file={enable_file}, structured={enable_structured}"
    )


def log_error_context(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    operation: Optional[str] = None,
) -> None:
    """
    Log an error with comprehensive context information.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context information
        operation: Description of the operation that failed
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "operation": operation or "unknown",
    }

    if context:
        # Filter sensitive data from context
        filtered_context = {}
        for key, value in context.items():
            if any(
                sensitive in key.lower() for sensitive in ["password", "token", "secret", "key"]
            ):
                filtered_context[key] = "[FILTERED]"
            else:
                filtered_context[key] = str(value)[:200]  # Truncate long values
        error_info["context"] = filtered_context

    logger.error(
        f"Operation '{error_info['operation']}' failed: {error_info['error_message']}",
        extra={"error_context": error_info},
        exc_info=True,
    )
