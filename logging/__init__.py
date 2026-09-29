"""
Logging Package for Orvix Sphere.
Integrates standard Python logging with Orvix's ErrorLogger and error hooks.
Preserves full standard library logging functionality while exporting error tools.
"""

from __future__ import annotations
import sys
import os
import importlib.util

# 1. Locate and bridge standard library logging so nothing in Python breaks
stdlib_logging_dir = None
for p in sys.path:
    if not p or p in (".", ""):
        continue
    cand = os.path.join(p, "logging")
    if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "__init__.py")):
        # Ensure it is not this current workspace directory
        this_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.abspath(cand).lower() != this_dir.lower():
            stdlib_logging_dir = cand
            break

if stdlib_logging_dir and "__path__" in globals():
    # Extend package path so submodule imports like `import logging.handlers` work
    if stdlib_logging_dir not in __path__:
        __path__.append(stdlib_logging_dir)

    init_file = os.path.join(stdlib_logging_dir, "__init__.py")
    spec = importlib.util.spec_from_file_location("_stdlib_logging", init_file)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_stdlib_logging"] = mod
        spec.loader.exec_module(mod)
        for attr in dir(mod):
            if not attr.startswith("__"):
                globals()[attr] = getattr(mod, attr)

# 2. Export Orvix ErrorLogger and error hooks
try:
    from .error_logger import ErrorLogger, error_logger
except ImportError:
    pass

try:
    from .error_hook import setup_global_exception_hook, capture_uncaught, capture_error
except ImportError:
    pass

__all__ = [
    "ErrorLogger",
    "error_logger",
    "setup_global_exception_hook",
    "capture_uncaught",
    "capture_error",
]
