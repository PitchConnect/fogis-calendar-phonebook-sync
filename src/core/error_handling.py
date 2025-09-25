"""
Enhanced error handling for FOGIS Calendar & Phonebook Sync service.

This module provides comprehensive error handling with context preservation,
retry logic, and circuit breaker patterns following the v2.1.0 standard.
"""

import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, Optional, Type, Union

from .logging_config import log_error_context


class CalendarSyncError(Exception):
    """Base exception for calendar sync operations."""

    pass


class AuthenticationError(CalendarSyncError):
    """Raised when authentication fails."""

    pass


class CalendarAPIError(CalendarSyncError):
    """Raised when Google Calendar API operations fail."""

    pass


class ContactsAPIError(CalendarSyncError):
    """Raised when Google Contacts API operations fail."""

    pass


class FogisAPIError(CalendarSyncError):
    """Raised when FOGIS API operations fail."""

    pass


class ConfigurationError(CalendarSyncError):
    """Raised when configuration is invalid."""

    pass


def handle_calendar_errors(operation_name: str, component: str = "calendar_sync"):
    """
    Decorator for handling calendar sync errors with enhanced logging.

    Args:
        operation_name: Name of the operation being performed
        component: Component name for logging context
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            logger.info(f"Starting {operation_name}")

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Successfully completed {operation_name} in {duration:.2f}s")
                return result

            except AuthenticationError as e:
                log_error_context(
                    logger,
                    e,
                    {
                        "operation": operation_name,
                        "component": component,
                        "function": func.__name__,
                        "error_category": "authentication",
                        "duration": time.time() - start_time,
                    },
                )
                raise

            except (CalendarAPIError, ContactsAPIError) as e:
                log_error_context(
                    logger,
                    e,
                    {
                        "operation": operation_name,
                        "component": component,
                        "function": func.__name__,
                        "error_category": "api_error",
                        "duration": time.time() - start_time,
                    },
                )
                raise

            except FogisAPIError as e:
                log_error_context(
                    logger,
                    e,
                    {
                        "operation": operation_name,
                        "component": component,
                        "function": func.__name__,
                        "error_category": "fogis_api",
                        "duration": time.time() - start_time,
                    },
                )
                raise

            except ConfigurationError as e:
                log_error_context(
                    logger,
                    e,
                    {
                        "operation": operation_name,
                        "component": component,
                        "function": func.__name__,
                        "error_category": "configuration",
                        "duration": time.time() - start_time,
                    },
                )
                raise

            except Exception as e:
                log_error_context(
                    logger,
                    e,
                    {
                        "operation": operation_name,
                        "component": component,
                        "function": func.__name__,
                        "error_category": "unexpected",
                        "duration": time.time() - start_time,
                        "args_summary": str(args)[:200] if args else None,
                        "kwargs_summary": (
                            {k: str(v)[:100] for k, v in kwargs.items()} if kwargs else None
                        ),
                    },
                )
                raise

        return wrapper

    return decorator


def handle_api_errors(operation_name: str, retry_count: int = 3, backoff_factor: float = 1.0):
    """
    Decorator for handling API errors with retry logic.

    Args:
        operation_name: Name of the operation being performed
        retry_count: Number of retry attempts
        backoff_factor: Exponential backoff factor
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)

            for attempt in range(retry_count + 1):
                try:
                    if attempt > 0:
                        wait_time = backoff_factor * (2 ** (attempt - 1))
                        logger.info(
                            f"Retrying {operation_name} (attempt {attempt + 1}/{retry_count + 1}) "
                            f"after {wait_time:.1f}s delay"
                        )
                        time.sleep(wait_time)

                    return func(*args, **kwargs)

                except (CalendarAPIError, ContactsAPIError, FogisAPIError) as e:
                    if attempt == retry_count:
                        log_error_context(
                            logger,
                            e,
                            {
                                "operation": operation_name,
                                "function": func.__name__,
                                "final_attempt": True,
                                "total_attempts": attempt + 1,
                            },
                        )
                        raise
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {e}")

                except Exception as e:
                    # Don't retry for non-API errors
                    log_error_context(
                        logger,
                        e,
                        {
                            "operation": operation_name,
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "non_retryable_error": True,
                        },
                    )
                    raise

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.

    Prevents cascading failures by temporarily disabling calls to failing services.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CalendarSyncError: When circuit is open
        """
        logger = logging.getLogger(__name__)

        if self.state == "OPEN":
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise CalendarSyncError("Circuit breaker is OPEN. Service unavailable.")
            else:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")

        try:
            result = func(*args, **kwargs)

            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")

            return result

        except Exception:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")

            raise


def safe_execute(
    func: Callable,
    operation_name: str,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs,
) -> Any:
    """
    Safely execute a function with comprehensive error handling.

    Args:
        func: Function to execute
        operation_name: Name of the operation for logging
        default_return: Value to return on error
        log_errors: Whether to log errors
        **kwargs: Additional arguments to pass to function

    Returns:
        Function result or default_return on error
    """
    logger = logging.getLogger(__name__)

    try:
        return func(**kwargs)
    except Exception as e:
        if log_errors:
            log_error_context(
                logger,
                e,
                {
                    "operation": operation_name,
                    "function": (func.__name__ if hasattr(func, "__name__") else str(func)),
                    "safe_execution": True,
                    "default_return": str(default_return),
                },
            )
        return default_return


def validate_configuration(config: Dict[str, Any], required_keys: list) -> None:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary
        required_keys: List of required configuration keys

    Raises:
        ConfigurationError: When required keys are missing
    """
    missing_keys = [key for key in required_keys if key not in config or not config[key]]

    if missing_keys:
        raise ConfigurationError(f"Missing required configuration keys: {missing_keys}")


def create_error_context(
    operation: str, component: str, additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized error context dictionary.

    Args:
        operation: Operation being performed
        component: Component name
        additional_context: Additional context information

    Returns:
        Error context dictionary
    """
    context = {
        "operation": operation,
        "component": component,
        "timestamp": time.time(),
        "stack_trace": traceback.format_stack()[-3:-1],  # Get relevant stack frames
    }

    if additional_context:
        context.update(additional_context)

    return context
