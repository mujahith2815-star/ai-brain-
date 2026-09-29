"""
Pytest global configuration and fixtures for P.H.A.S.S test suites.
Configures Tcl/Tk paths and manages global hardware daemon state.
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure Windows Python Tcl/Tk environment variables are reliably populated
tcl_path = os.path.join(sys.base_prefix, "tcl", "tcl8.6")
tk_path = os.path.join(sys.base_prefix, "tcl", "tk8.6")
if os.path.exists(tcl_path):
    os.environ["TCL_LIBRARY"] = tcl_path
if os.path.exists(tk_path):
    os.environ["TK_LIBRARY"] = tk_path


@pytest.fixture(autouse=True)
def reset_daemon_state():
    """Ensures background daemon is restored to default connected state after each test."""
    yield
    try:
        from core.background_daemon import background_daemon
        background_daemon.simulate_hotplug("connect", board="ESP32", port="COM3")
    except Exception:
        pass
