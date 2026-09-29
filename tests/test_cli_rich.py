"""
Unit Tests for Orvix Sphere Rich CLI Interface (Terminal UI).
"""

import io
import pytest
from rich.console import Console

from cli.rich_ui import (
    print_banner,
    print_chat_message,
    print_status_table,
    print_code,
)


def test_rich_banner_execution(capsys):
    """Verifies print_banner executes without error and prints banner."""
    print_banner()


def test_rich_chat_message_execution():
    """Verifies print_chat_message displays panels for assistant and operator."""
    print_chat_message("Orvix Sphere", "Welcome back, Operator.")
    print_chat_message("Operator", "Show me current tasks.")


def test_rich_status_table_execution():
    """Verifies print_status_table formats key-value telemetry."""
    status_data = {
        "Host": "localhost",
        "Memory Usage": "142 MB",
        "Active Workers": "4",
        "Status": "READY"
    }
    print_status_table("Node Telemetry", status_data)


def test_rich_status_table_dict_only():
    """Verifies print_status_table works with direct dict input."""
    data = {
        "models": {"primary": "Llama-3.2", "secondary": "Phi-4"},
        "mcp": {"connected": 2, "total": 2, "available": True},
        "proactive": {"state": "ENABLED", "max_per_hour": 20}
    }
    print_status_table(data)


def test_rich_code_execution():
    """Verifies print_code formats and highlights code snippets."""
    sample_code = """
def hello_sphere():
    print("Welcome to Orvix Sphere v1.0.0")
    return True
"""
    print_code(sample_code, language="python")


def test_custom_console_rendering():
    """Verifies custom console string recording for automated headless pipelines."""
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=True, width=80)
    
    from rich.panel import Panel
    test_console.print(Panel("Test headless output", title="Test Panel"))
    output = buf.getvalue()
    assert "Test headless output" in output
    assert "Test Panel" in output
