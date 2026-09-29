"""
Global Exception Hook & Error Interceptors for Orvix Sphere.
Captures uncaught exceptions and structured errors, logging them
to ErrorLogger with execution context for Antigravity repair workflows.
"""

from __future__ import annotations
import functools
import inspect
import sys
import traceback
from typing import Any, Callable, Dict, Optional

from .error_logger import error_logger


def capture_uncaught(exc_type: Any, exc_value: Any, exc_traceback: Any):
    """Global sys.excepthook interceptor."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    source_file = ""
    function_name = ""
    if exc_traceback:
        last_frame = traceback.extract_tb(exc_traceback)[-1]
        source_file = f"{last_frame.filename}:{last_frame.lineno}"
        function_name = last_frame.name

    error_dict = {
        "category": "UNCAUGHT_EXCEPTION",
        "error_type": exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type),
        "error_message": str(exc_value),
        "traceback": tb_str,
        "source_file": source_file,
        "function_name": function_name,
        "context": {
            "source": "sys.excepthook",
            "reproduce": "Uncaught global exception",
        },
    }
    try:
        error_logger.log(error_dict)
    except Exception:
        pass

    # Still invoke default hook to output to stderr
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_global_exception_hook():
    """Installs capture_uncaught as sys.excepthook."""
    sys.excepthook = capture_uncaught


def capture_error(
    error: Any,
    category: str = "GENERAL",
    context: Optional[Dict[str, Any]] = None,
    source_file: Optional[str] = None,
    function_name: Optional[str] = None,
) -> int:
    """
    Manually captures an exception or error message, writes to ErrorLogger,
    and returns the assigned error ID.
    """
    ctx = context or {}
    if isinstance(error, Exception):
        err_type = type(error).__name__
        err_msg = str(error)
        tb_str = traceback.format_exc()
        if not source_file:
            tb = error.__traceback__
            if tb:
                extracted = traceback.extract_tb(tb)
                if extracted:
                    last_frame = extracted[-1]
                    source_file = f"{last_frame.filename}:{last_frame.lineno}"
                    function_name = function_name or last_frame.name
    else:
        err_type = "ExplicitError"
        err_msg = str(error)
        tb_str = ""

    payload = {
        "category": category,
        "error_type": err_type,
        "error_message": err_msg,
        "traceback": tb_str,
        "source_file": source_file or "unknown",
        "function_name": function_name or "unknown",
        "context": ctx,
    }
    return error_logger.log(payload)


def wrap_errors(category: str = "FUNCTION_ERROR"):
    """Decorator to catch and log errors in high-risk functions."""
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                src = inspect.getsourcefile(func) or func.__code__.co_filename
                line = func.__code__.co_firstlineno
                capture_error(
                    e,
                    category=category,
                    source_file=f"{src}:{line}",
                    function_name=func.__name__,
                    context={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                )
                raise
        return wrapper
    return decorator
