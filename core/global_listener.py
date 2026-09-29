"""
Global Quick-Action Hotkey & System Tray Listener for P.H.A.S.S Sphere.
Binds Ctrl+Space globally to trigger a floating quick-directive overlay or voice capture.
Silently dispatches queries to process_query() and displays results as non-intrusive,
transparent 5-second toast notifications without requiring the terminal or main window.
Runs as a permanent background system tray icon using pystray.
"""

from __future__ import annotations
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PIL import Image, ImageDraw

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    pystray = None
    PYSTRAY_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    keyboard = None
    KEYBOARD_AVAILABLE = False

import tkinter as tk
from tkinter import ttk

from core.silent_logger import silent_logger


def create_tray_icon_image(state: str = "listening") -> Image.Image:
    """
    Generates a 64x64 cosmic holographic tray icon.
    Supports state indicators:
    - 'listening': Pulsing cyan dot confirming active listening (not recording).
    - 'recording': Radiant crimson/amber dot confirming active speech recording.
    - 'idle': Standard cosmic core.
    """
    size = (64, 64)
    img = Image.new("RGBA", size, (10, 10, 26, 255))
    draw = ImageDraw.Draw(img)
    # Outer glowing cyan ring
    draw.ellipse([4, 4, 60, 60], outline=(0, 240, 255, 255), width=3)

    if state == "listening":
        # Inner dark core
        draw.ellipse([14, 14, 50, 50], fill=(12, 20, 36, 230), outline=(0, 200, 255, 160), width=1)
        # Pulsing vibrant cyan dot
        draw.ellipse([24, 24, 40, 40], fill=(0, 240, 255, 255), outline=(150, 255, 255, 255), width=2)
    elif state == "recording":
        # Inner fiery core
        draw.ellipse([14, 14, 50, 50], fill=(45, 10, 20, 230), outline=(255, 60, 100, 180), width=1)
        # Active recording dot
        draw.ellipse([24, 24, 40, 40], fill=(255, 50, 80, 255), outline=(255, 180, 200, 255), width=2)
    else:
        # Standard purple core
        draw.ellipse([14, 14, 50, 50], fill=(157, 0, 255, 220), outline=(0, 240, 255, 180), width=1)
        draw.ellipse([27, 27, 37, 37], fill=(255, 255, 255, 255))

    return img


class FloatingToastWindow:
    """Non-intrusive floating cosmic toast notification widget."""

    def __init__(self, title: str, message: str, duration: int = 5):
        self.title = title
        self.message = message
        self.duration = duration
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-alpha", 0.0)

            toast = tk.Toplevel(root)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg="#0c0c20")

            # Determine screen size & position at bottom right
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            w, h = 380, 110
            x = screen_w - w - 24
            y = screen_h - h - 60
            toast.geometry(f"{w}x{h}+{x}+{y}")

            # Border canvas wrapper
            border_frame = tk.Frame(toast, bg="#00f0ff", padx=1, pady=1)
            border_frame.pack(fill="both", expand=True)

            card = tk.Frame(border_frame, bg="#0e0e28", padx=12, pady=8)
            card.pack(fill="both", expand=True)

            # Header
            hdr_frame = tk.Frame(card, bg="#0e0e28")
            hdr_frame.pack(fill="x", anchor="w")
            tk.Label(
                hdr_frame,
                text=f"◈ {self.title}",
                font=("Segoe UI", 10, "bold"),
                fg="#00f0ff",
                bg="#0e0e28",
            ).pack(side="left")

            tk.Label(
                hdr_frame,
                text="[P.H.A.S.S]",
                font=("Consolas", 8),
                fg="#8e8ea8",
                bg="#0e0e28",
            ).pack(side="right")

            # Body text (up to 3 lines)
            clean_msg = self.message.strip()
            if len(clean_msg) > 160:
                clean_msg = clean_msg[:157] + "..."

            tk.Label(
                card,
                text=clean_msg,
                font=("Segoe UI", 9),
                fg="#ffffff",
                bg="#0e0e28",
                justify="left",
                wraplength=350,
                anchor="w",
            ).pack(fill="both", expand=True, pady=(4, 0))

            # Auto close after duration seconds
            toast.after(int(self.duration * 1000), lambda: (toast.destroy(), root.destroy()))
            root.mainloop()
        except Exception as e:
            silent_logger.log("toast_error", f"Floating toast failed: {e}", error=str(e))


def show_toast(title: str, message: str, duration: int = 5) -> None:
    """
    Displays a non-blocking toast notification across Windows and Linux.
    Uses tray icon notification if running, and displays the floating cosmic toast.
    """
    silent_logger.log("toast_notification", f"[{title}] {message}")

    # 1. Native Tray Notification if listener is running
    global global_listener_instance
    if global_listener_instance and global_listener_instance.icon and global_listener_instance.is_running:
        try:
            global_listener_instance.icon.notify(message, title)
        except Exception:
            pass

    # 2. Universal Cosmic Floating Toast Window
    try:
        FloatingToastWindow(title, message, duration=duration)
    except Exception:
        pass


class GlobalQuickActionOverlay:
    """Floating borderless prompt window for typing or speaking directives."""

    def __init__(self, on_submit: Callable[[str], None]):
        self.on_submit = on_submit
        self.root: Optional[tk.Tk] = None

    def show(self):
        """Displays the quick overlay centered on screen."""
        threading.Thread(target=self._run_ui, daemon=True).start()

    def _run_ui(self):
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.configure(bg="#00f0ff")

            w, h = 540, 68
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = int(sh * 0.28)  # Placed prominently in upper third of display
            self.root.geometry(f"{w}x{h}+{x}+{y}")

            inner = tk.Frame(self.root, bg="#0c0c24", padx=10, pady=8)
            inner.pack(fill="both", expand=True, padx=2, pady=2)

            # Left glyph
            tk.Label(
                inner,
                text="⚡ P.H.A.S.S",
                font=("Segoe UI", 11, "bold"),
                fg="#00f0ff",
                bg="#0c0c24",
            ).pack(side="left", padx=(4, 10))

            # Entry
            entry_var = tk.StringVar()
            entry = tk.Entry(
                inner,
                textvariable=entry_var,
                font=("Segoe UI", 11),
                bg="#141436",
                fg="#ffffff",
                insertbackground="#00f0ff",
                relief="flat",
                highlightthickness=1,
                highlightbackground="#343468",
                highlightcolor="#00f0ff",
            )
            entry.pack(side="left", fill="both", expand=True, padx=4, ipady=4)
            entry.focus_set()

            def _submit(event=None):
                text = entry_var.get().strip()
                if self.root:
                    self.root.destroy()
                    self.root = None
                if text:
                    self.on_submit(text)
                else:
                    # If user hit enter on empty prompt, trigger voice capture
                    self._trigger_voice()

            def _cancel(event=None):
                if self.root:
                    self.root.destroy()
                    self.root = None

            def _mic_clicked():
                if self.root:
                    self.root.destroy()
                    self.root = None
                self._trigger_voice()

            entry.bind("<Return>", _submit)
            entry.bind("<Escape>", _cancel)

            # Mic button
            btn_mic = tk.Button(
                inner,
                text="🎙️",
                font=("Segoe UI", 11),
                bg="#1a1a44",
                fg="#00f0ff",
                activebackground="#00f0ff",
                activeforeground="#000000",
                relief="flat",
                bd=0,
                padx=8,
                command=_mic_clicked,
            )
            btn_mic.pack(side="right", padx=(6, 2))

            # Transmit button
            btn_send = tk.Button(
                inner,
                text="Transmit",
                font=("Segoe UI", 9, "bold"),
                bg="#00f0ff",
                fg="#0a0a1a",
                activebackground="#9d00ff",
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                padx=10,
                command=_submit,
            )
            btn_send.pack(side="right", padx=4)

            self.root.mainloop()
        except Exception as e:
            silent_logger.log("overlay_error", f"Quick Action overlay error: {e}", error=str(e))

    def _trigger_voice(self):
        """Silently listens for voice command via voice_interface."""
        try:
            from core.voice_interface import get_voice_interface
            voice = get_voice_interface()
            show_toast("P.H.A.S.S Voice", "🎙️ Listening for command...", duration=3)
            cmd = voice.listen_command()
            if cmd:
                self.on_submit(cmd)
            else:
                show_toast("P.H.A.S.S", "No speech detected. Try again.", duration=3)
        except Exception as e:
            silent_logger.log("voice_trigger_error", str(e), error=str(e))


class GlobalListener:
    """
    Background listener providing global hotkey (Ctrl+Space),
    floating quick prompt overlay, system tray icon, and silent toast notifications.
    """

    def __init__(self):
        self.icon: Optional[pystray.Icon] = None
        self.is_running = False
        self._hotkey_hook = None

    def trigger_quick_prompt(self):
        """Opens the floating quick-action prompt overlay."""
        silent_logger.log("global_listener", "Ctrl+Space hotkey triggered")
        overlay = GlobalQuickActionOverlay(on_submit=self._dispatch_query_silently)
        overlay.show()

    def _dispatch_query_silently(self, query: str):
        """Silently processes query and shows toast notification without terminal interaction."""
        def _worker():
            try:
                from nlp.answer_pipeline import process_query
                response = process_query(query)
                show_toast("P.H.A.S.S", response, duration=5)
            except Exception as e:
                import traceback
                silent_logger.log("query_dispatch_error", str(e), raw_trace=traceback.format_exc(), error=str(e))
                show_toast("P.H.A.S.S", "Action completed.", duration=4)

        threading.Thread(target=_worker, daemon=True).start()

    def trigger_morning_routine(self):
        """Triggers the Morning Autopilot directly from the tray icon."""
        def _worker():
            try:
                from core.morning_autopilot import morning_autopilot
                res = morning_autopilot.execute_routine(notify=True)
            except Exception as e:
                silent_logger.log("tray_morning_error", str(e), error=str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def launch_hud(self):
        """Launches the full Holographic HUD interface."""
        def _worker():
            try:
                import subprocess
                subprocess.Popen([sys.executable, "fix_and_launch.py"])
            except Exception as e:
                silent_logger.log("hud_launch_error", str(e), error=str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def start(self, run_detached: bool = True):
        """Registers hotkey and starts system tray icon."""
        if self.is_running:
            return

        self.is_running = True
        self.voice_state = "listening"
        silent_logger.log("global_listener", "Starting Global Quick-Action Listener")

        # 1. Register Global Hotkeys (Ctrl+Space and Ctrl+Shift+P)
        if KEYBOARD_AVAILABLE and keyboard:
            try:
                self._hotkey_hook = keyboard.add_hotkey("ctrl+space", self.trigger_quick_prompt)
                self._hud_hotkey_hook = keyboard.add_hotkey("ctrl+shift+p", self.launch_hud)
                silent_logger.log("global_listener", "Bound global hotkeys: Ctrl+Space (Quick Directive), Ctrl+Shift+P (Holographic HUD)")
            except Exception as e:
                silent_logger.log("hotkey_error", f"Could not bind keyboard hotkey: {e}", error=str(e))

        # 2. Start System Tray Icon
        if PYSTRAY_AVAILABLE and pystray:
            try:
                tray_image = create_tray_icon_image("listening")
                menu = pystray.Menu(
                    pystray.MenuItem("⚡ Quick Directive (Ctrl+Space)", lambda: self.trigger_quick_prompt()),
                    pystray.MenuItem("💻 Show Holographic HUD (Ctrl+Shift+P)", lambda: self.launch_hud()),
                    pystray.MenuItem("🎙️ Voice Directive", lambda: self._trigger_voice_direct()),
                    pystray.MenuItem("☀️ Run Morning Routine", lambda: self.trigger_morning_routine()),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("❌ Exit P.H.A.S.S", lambda: self.stop()),
                )
                self.icon = pystray.Icon("phass_sphere", tray_image, "P.H.A.S.S Sovereign Intelligence", menu=menu)

                if run_detached:
                    threading.Thread(target=self.icon.run, daemon=True).start()
                else:
                    self.icon.run()
            except Exception as e:
                silent_logger.log("tray_init_error", f"Could not initialize system tray: {e}", error=str(e))

    def _trigger_voice_direct(self):
        overlay = GlobalQuickActionOverlay(on_submit=self._dispatch_query_silently)
        overlay._trigger_voice()

    def set_tray_state(self, state: str = "listening"):
        """Updates the system tray icon to reflect listening vs recording vs idle."""
        self.voice_state = state
        if self.icon:
            try:
                self.icon.icon = create_tray_icon_image(state)
            except Exception:
                pass

    def stop(self):
        """Stops tray icon and unbinds hotkey."""
        self.is_running = False
        if KEYBOARD_AVAILABLE and keyboard:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        silent_logger.log("global_listener", "Global Quick-Action Listener stopped")


global_listener_instance: Optional[GlobalListener] = None


def get_global_listener() -> GlobalListener:
    """Returns singleton GlobalListener instance."""
    global global_listener_instance
    if global_listener_instance is None:
        global_listener_instance = GlobalListener()
    return global_listener_instance


def start_global_listener() -> GlobalListener:
    """Starts the global listener in background and returns instance."""
    listener = get_global_listener()
    listener.start(run_detached=True)
    return listener


if __name__ == "__main__":
    print("Starting P.H.A.S.S Zero-Friction Global Listener & System Tray...")
    listener = start_global_listener()
    print("Running in system tray. Press Ctrl+Space anywhere to trigger quick directive.")
    try:
        while listener.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Stopped.")
