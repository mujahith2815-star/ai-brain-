"""
Holographic HUD Cyber Theme for P.H.A.S.S Sphere v9.0.
Implements deep space palette, glass-morphism panels, glowing neon cyan/purple accents,
and futuristic typography for CustomTkinter desktop interface.
"""

from __future__ import annotations
import tkinter.font as tkfont
from typing import Dict, Any, Tuple

# Core Holographic Cyber Palette
HOLO_PALETTE: Dict[str, str] = {
    "bg": "#0a0a1a",              # Deep cosmic space
    "bg_secondary": "#0f0f26",    # Secondary space layer
    "panel_bg": "#14142e",        # Glass panel surface
    "panel_hover": "#1c1c3f",     # Glass panel hover
    "card_bg": "#18183a",         # Elevated cyber card
    "border_cyan": "#00f0ff",     # Primary Neon Cyan (borders & headers)
    "accent_purple": "#7b2ffc",   # Secondary Electric Purple (action buttons)
    "accent_purple_hover": "#934bfd",
    "text_glowing": "#e0f2fe",    # Glowing Cyan / White text
    "text_secondary": "#8da7be",  # Subdued telemetry text
    "text_muted": "#52687d",      # Muted labels
    "scanline_cyan": "#00f0ff",   # Scanning radar sweep
    "pulse_purple": "#a855f7",    # Voice pulse state
    "status_ok": "#00f0ff",       # System verified
    "status_warn": "#f59e0b",     # Caution
    "status_err": "#ef4444",      # Fault
}

# Holographic Symbol Glyphs
HOLO_ICONS = {
    "online": "◈",
    "processing": "⟡",
    "idle": "◇",
    "radar": "⌖",
    "cpu": "⚡",
    "ram": "▦",
    "disk": "💾",
    "hardware": "🔌",
    "shield": "🛡",
    "voice": "🎙",
    "skill": "🔮",
}


def get_hud_font(font_type: str = "body", size: int = 11, bold: bool = False) -> Tuple[str, int, str]:
    """
    Returns available font with futuristic preference (Orbitron, Share Tech Mono, Consolas, Segoe UI).
    """
    weight = "bold" if bold else "normal"
    # Available fonts detection
    try:
        families = [f.lower() for f in tkfont.families()]
    except Exception:
        families = []

    if font_type in ("header", "title"):
        if "orbitron" in families:
            return ("Orbitron", size, weight)
        if "share tech mono" in families:
            return ("Share Tech Mono", size, weight)
        return ("Consolas", size, weight)

    if font_type == "mono":
        if "share tech mono" in families:
            return ("Share Tech Mono", size, weight)
        return ("Consolas", size, weight)

    return ("Segoe UI", size, weight)


def apply_holographic_theme_to_ctk():
    """Configures global CustomTkinter appearance mode."""
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
    except Exception:
        pass
