"""
Reusable UI Components for P.H.A.S.S Desktop Assistant.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict
from ui.styles import DARK_THEME, FONTS, attach_button_hover


class WorkspaceTab(tk.Button):
    """Interactive workspace selector button with active state highlight."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        colors: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        self.colors = colors or DARK_THEME
        self.workspace_name = text
        self.is_active = False

        super().__init__(
            parent,
            text=text,
            bg=self.colors["bg3"],
            fg=self.colors["text"],
            relief=tk.FLAT,
            padx=15,
            pady=5,
            font=FONTS["button"],
            command=command,
            **kwargs,
        )
        attach_button_hover(self, normal_bg=self.colors["bg3"], hover_bg=self.colors["accent"])

    def set_active(self, active: bool):
        self.is_active = active
        if active:
            self.configure(bg=self.colors["accent2"], fg=self.colors["text"])
        else:
            self.configure(bg=self.colors["bg3"], fg=self.colors["text"])


class QuickToolButton(tk.Button):
    """Sidebar quick tool action launcher button with hover effect."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        colors: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        self.colors = colors or DARK_THEME
        super().__init__(
            parent,
            text=text,
            bg=self.colors["bg3"],
            fg=self.colors["text"],
            relief=tk.FLAT,
            padx=10,
            pady=5,
            anchor=tk.W,
            font=FONTS["button"],
            command=command,
            **kwargs,
        )
        attach_button_hover(self, normal_bg=self.colors["bg3"], hover_bg=self.colors["accent"])


class StatCard(ttk.Frame):
    """Displays telemetry metric with icon, title, and live value."""

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        initial_value: str = "0%",
        colors: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        self.colors = colors or DARK_THEME
        super().__init__(parent, style="Card.TFrame", **kwargs)

        self.label = ttk.Label(self, text=label_text, style="Subtitle.TLabel")
        self.label.pack(anchor=tk.W, padx=6, pady=(4, 0))

        self.value_label = ttk.Label(self, text=initial_value, style="Dark.TLabel", font=FONTS["body_bold"])
        self.value_label.pack(anchor=tk.W, padx=6, pady=(0, 4))

    def update_value(self, new_value: str):
        self.value_label.config(text=new_value)
