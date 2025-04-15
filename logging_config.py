"""Logging configuration module.

This module configures structured logging for the application using structlog.
It provides consistent logging format, log rotation, and context preservation.
"""

import logging
import logging.handlers
import os
import sys
import time
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to format logs as JSON (True) or human-readable (False)
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Set the log level
    log_level_obj = getattr(logging, log_level.upper())

    # Configure standard library logging
    logging.basicConfig(
        level=log_level_obj,
        format="%(message)s",
        handlers=[],  # We'll add handlers manually
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Create rotating file handler for JSON logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename="logs/application.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,
    )

    # Configure formatters based on format preference
    if json_format:
        # JSON formatter for structured logging
        json_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
        console_handler.setFormatter(json_formatter)
        file_handler.setFormatter(json_formatter)
    else:
        # Human-readable formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_request_id() -> str:
    """Generate a unique request ID for tracking requests across logs.

    Returns:
        A string containing a unique request identifier
    """
    # Import uuid here to avoid circular imports
    import uuid  # pylint: disable=import-outside-toplevel

    return str(uuid.uuid4())


def add_request_context_to_logs(request_id: Optional[str] = None) -> Dict[str, Any]:
    """Add request context to the log context.

    Args:
        request_id: Optional request ID. If not provided, a new one will be generated.

    Returns:
        A dictionary with context information to be included in logs
    """
    if request_id is None:
        request_id = get_request_id()

    return {
        "request_id": request_id,
        "timestamp": time.time(),
    }
