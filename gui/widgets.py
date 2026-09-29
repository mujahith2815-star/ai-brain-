"""
Cybernetic UI Widgets and Styling for the P.H.A.S.S Sphere Desktop Application.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

# Color Palette
BG_MAIN = "#06090e"
BG_PANEL = "#0b111a"
BG_CARD = "#101926"
BORDER_CYAN = "#00f0ff"
BORDER_MUTED = "#1e293b"
TEXT_MAIN = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"
COLOR_CYAN = "#00f0ff"
COLOR_EMERALD = "#10b981"
COLOR_AMBER = "#f59e0b"
COLOR_ROSE = "#f43f5e"


class CyberMeter(tk.Canvas):
    def __init__(self, parent: tk.Widget, width: int = 140, height: int = 16, color: str = COLOR_CYAN):
        super().__init__(parent, width=width, height=height, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_MUTED)
        self.width = width
        self.height = height
        self.color = color
        self.value_pct = 0.0

    def set_value(self, pct: float, color: Optional[str] = None) -> None:
        self.value_pct = max(0.0, min(100.0, pct))
        if color:
            self.color = color
        self.delete("all")

        fill_w = int((self.value_pct / 100.0) * (self.width - 2))
        if fill_w > 0:
            self.create_rectangle(1, 1, fill_w, self.height - 1, fill=self.color, outline="")

        self.create_text(
            self.width // 2, self.height // 2,
            text=f"{self.value_pct:.1f}%",
            fill=TEXT_MAIN,
            font=("Consolas", 8, "bold"),
        )


class CyberCard(tk.Frame):
    def __init__(self, parent: tk.Widget, label: str, value: str = "--", value_color: str = COLOR_CYAN):
        super().__init__(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER_MUTED, padx=6, pady=4)
        self.lbl = tk.Label(self, text=label.upper(), bg=BG_CARD, fg=TEXT_DIM, font=("Consolas", 7, "bold"))
        self.lbl.pack(anchor="w")
        self.val_lbl = tk.Label(self, text=value, bg=BG_CARD, fg=value_color, font=("Consolas", 10, "bold"))
        self.val_lbl.pack(anchor="w")

    def update_val(self, val: str, color: Optional[str] = None) -> None:
        self.val_lbl.config(text=val)
        if color:
            self.val_lbl.config(fg=color)
