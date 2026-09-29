"""
UI Styling, Themes, and Color Schemes for P.H.A.S.S Desktop Assistant.
"""

from typing import Dict, Any
import tkinter as tk
from tkinter import ttk

# Modern Dark Cyberpunk / Obsidian Theme
DARK_THEME: Dict[str, str] = {
    "bg": "#1a1a2e",
    "bg2": "#16213e",
    "bg3": "#0f3460",
    "accent": "#533483",
    "accent2": "#e94560",
    "text": "#ffffff",
    "text2": "#a8a8b8",
    "user_msg": "#533483",
    "assistant_msg": "#1a3a5c",
    "system_msg": "#2d2d44",
    "card_bg": "#12182b",
    "border": "#283452",
    "success": "#00b894",
    "warning": "#fdcb6e",
    "danger": "#d63031",
}

FONTS: Dict[str, tuple] = {
    "title": ("Segoe UI", 16, "bold"),
    "subtitle": ("Segoe UI", 10),
    "body": ("Segoe UI", 11),
    "body_bold": ("Segoe UI", 11, "bold"),
    "button": ("Segoe UI", 9),
    "timestamp": ("Segoe UI", 8),
    "small": ("Segoe UI", 9, "italic"),
    "stat_value": ("Segoe UI", 14, "bold"),
    "stat_label": ("Segoe UI", 9),
}


def configure_ttk_styles(root: tk.Tk, colors: Dict[str, str] = DARK_THEME) -> ttk.Style:
    """Configures global ttk style hierarchy."""
    root.configure(bg=colors["bg"])
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("Custom.TFrame", background=colors["bg"])
    style.configure("Card.TFrame", background=colors["card_bg"], relief="flat")
    style.configure("Dark.TLabel", background=colors["bg"], foreground=colors["text"])
    style.configure("Accent.TLabel", background=colors["bg"], foreground=colors["accent2"])
    style.configure("Title.TLabel", background=colors["bg"], foreground=colors["text"], font=FONTS["title"])
    style.configure("Subtitle.TLabel", background=colors["bg"], foreground=colors["text2"], font=FONTS["subtitle"])
    style.configure("Dark.TButton", background=colors["accent"], foreground=colors["text"], font=FONTS["button"])

    # LabelFrames
    style.configure("Custom.TLabelframe", background=colors["bg"], foreground=colors["text2"])
    style.configure("Custom.TLabelframe.Label", background=colors["bg"], foreground=colors["text2"], font=FONTS["subtitle"])

    return style


def attach_button_hover(
    button: tk.Button,
    normal_bg: str = DARK_THEME["bg3"],
    hover_bg: str = DARK_THEME["accent"],
):
    """Adds smooth hover background color transition to standard Tk button."""
    def on_enter(event):
        button.configure(bg=hover_bg)

    def on_leave(event):
        button.configure(bg=normal_bg)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
