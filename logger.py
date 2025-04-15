"""Logger module for the application.

This module provides a consistent way to get loggers throughout the application.
It ensures that all loggers have the same configuration and context.
"""

from typing import Any, Dict, Optional

import structlog


def get_logger(name: str):
    """Get a logger with the given name.

    Args:
        name: The name of the logger, typically __name__ of the calling module

    Returns:
        A configured structlog logger
    """
    # Configure structlog if not already configured
    if not structlog.is_configured():
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    return structlog.get_logger(name)


def bind_logger_context(
    logger: structlog.stdlib.BoundLogger, **context
) -> structlog.stdlib.BoundLogger:
    """Bind additional context to a logger.

    Args:
        logger: The logger to bind context to
        **context: Keyword arguments to add to the logger context

    Returns:
        A new logger with the additional context bound
    """
    return logger.bind(**context)


def with_context(context: Dict[str, Any]) -> structlog.stdlib.BoundLogger:
    """Get a logger with the given context.

    Args:
        context: The context to bind to the logger

    Returns:
        A configured structlog logger with the given context
    """
    return structlog.get_logger().bind(**context)
