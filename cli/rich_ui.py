"""
Rich Console Interface for Orvix Sphere.
Provides colorful panels, tables, banners, and progress bars using the 'rich' library.
"""

from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

BANNER_ART = r"""[bold cyan]
  ___  ______     _____ _  __   ____  ____  _   _ _____ ____  _____ 
 / _ \|  _ \ \   / /_ _| |/ /  / ___||  _ \| | | | ____|  _ \| ____|
| | | | |_) \ \ / / | || ' /   \___ \| |_) | |_| |  _| | |_) |  _|  
| |_| |  _ < \ V /  | || . \    ___) |  __/|  _  | |___|  _ <| |___ 
 \___/|_| \_\ \_/  |___|_|\_\  |____/|_|   |_| |_|_____|_| \_\_____|
[/bold cyan][bold white]             -- ORVIX SPHERE v1.4.0 | AUTONOMOUS COGNITIVE OS --[/bold white]
"""

def print_banner(extra_info: Optional[Dict[str, str]] = None) -> None:
    """Renders the stylized ASCII banner with subsystem status."""
    console.print(BANNER_ART)
    if extra_info:
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold cyan", justify="right")
        info_table.add_column(style="white")
        for k, v in extra_info.items():
            info_table.add_row(f"[{k}]", v)
        console.print(Panel(info_table, border_style="cyan", title="[bold white]System Initialization[/bold white]", subtitle="[dim]ORVIX SPHERE — Autonomous AI OS[/dim]"))

def print_chat_message(role: str, content: str, title: Optional[str] = None) -> None:
    """Renders a role-colored chat panel."""
    role_lower = role.lower()
    if role_lower in ("user", "operator"):
        border_style = "cyan"
        title = title or "Operator"
    elif role_lower in ("assistant", "agent", "orvix", "phass"):
        border_style = "green"
        title = title or "Orvix Sphere"
    elif role_lower in ("tool", "executor"):
        border_style = "yellow"
        title = title or "Tool Execution"
    else:
        border_style = "magenta"
        title = title or role.capitalize()

    console.print(Panel(content, border_style=border_style, title=f"[bold {border_style}]{title}[/bold {border_style}]", padding=(0, 1)))

def print_status_table(data_or_title: Any, data: Optional[Dict[str, Any]] = None) -> None:
    """Renders a structured telemetry status table."""
    if data is not None:
        title = str(data_or_title)
        items = data
    elif isinstance(data_or_title, str):
        title = data_or_title
        items = {}
    else:
        title = "Orvix Sphere Telemetry Grid"
        items = data_or_title or {}

    table = Table(title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan")
    table.add_column("Subsystem / Key", style="bold white", width=24)
    table.add_column("Status / Value", style="green")
    table.add_column("Mode / Health", style="cyan")

    if "models" in items or "mcp" in items:
        models = items.get("models", {})
        table.add_row("Primary Model", str(models.get("primary", "Llama-3.2")), "[bold green]ONLINE[/bold green]")
        table.add_row("Secondary Brain", str(models.get("secondary", "Phi-4")), "[bold green]ONLINE[/bold green]")

        mcp = items.get("mcp", {})
        mcp_st = f"{mcp.get('connected', 0)}/{mcp.get('total', 0)} Connected"
        table.add_row("Model Context Protocol", mcp_st, "Standby / Fallback" if not mcp.get("available") else "Active")

        proactive = items.get("proactive", {})
        p_st = proactive.get("state", "READY")
        table.add_row("Proactive Agent", p_st, f"Max {proactive.get('max_per_hour', 20)}/hr")
    else:
        for k, v in items.items():
            table.add_row(str(k), str(v), "[bold green]ONLINE[/bold green]")

    console.print(table)

def print_code(code: str, language: str = "python") -> None:
    """Syntax highlights a block of code."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)
