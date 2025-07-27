"""Common logging utilities."""

import time
from functools import wraps

import structlog

logger = structlog.get_logger(__name__)


def log_function_call(operation_name: str | None = None, log_args: bool = False, log_result: bool = False):
    """Decorator to log function calls with timing information.

    Args:
        operation_name: Custom name for the operation (defaults to function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()

            log_data = {"operation": name}
            if log_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs

            logger.info(f"Starting {name}", **log_data)

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                result_log_data = {
                    "operation": name,
                    "duration_seconds": round(duration, 3),
                    "status": "success"
                }

                if log_result:
                    result_log_data["result"] = result

                logger.info(f"Completed {name}", **result_log_data)
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {name}",
                    operation=name,
                    duration_seconds=round(duration, 3),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()

            log_data = {"operation": name}
            if log_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs

            logger.info(f"Starting {name}", **log_data)

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                result_log_data = {
                    "operation": name,
                    "duration_seconds": round(duration, 3),
                    "status": "success"
                }

                if log_result:
                    result_log_data["result"] = result

                logger.info(f"Completed {name}", **result_log_data)
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {name}",
                    operation=name,
                    duration_seconds=round(duration, 3),
                    status="error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_api_request(endpoint: str, method: str = "GET", **context):
    """Log an API request with consistent format.

    Args:
        endpoint: API endpoint being called
        method: HTTP method
        **context: Additional context to log
    """
    logger.info(
        "API request",
        endpoint=endpoint,
        method=method,
        **context
    )
