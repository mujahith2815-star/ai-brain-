"""
Interactive Universal Remote Control Software for P.H.A.S.S Sphere v3.0.
Provides unified control for Smart TVs, Media Streaming, Audio Soundbars, AC Climate, and Smart Lights.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import time
import sys
import os
from typing import Dict, Any

# Theme Palette
BG_DARK = "#090d16"
BG_CARD = "#111827"
BG_ACCENT = "#1e293b"
CYAN = "#00f0ff"
AMBER = "#f59e0b"
EMERALD = "#10b981"
ROSE = "#ef4444"
TEXT_LIGHT = "#f8fafc"
TEXT_MUTED = "#94a3b8"


class UniversalRemoteApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("P.H.A.S.S SPHERE — UNIVERSAL REMOTE CONTROLLER v3.0")
        self.root.geometry("460x780")
        self.root.minsize(420, 720)
        self.root.configure(bg=BG_DARK)

        self.power_state = True
        self.current_volume = 32
        self.current_channel = 104
        self.ac_temp = 22
        self.ac_mode = "COOL"
        self.active_mode = "TV"

        self._build_ui()

    def _build_ui(self):
        # 1. Header Bar
        hdr = tk.Frame(self.root, bg=BG_CARD, height=50, padx=14, pady=8)
        hdr.pack(fill="x", side="top")

        tk.Label(hdr, text="P.H.A.S.S UNIVERSAL REMOTE", fg=CYAN, bg=BG_CARD, font=("Consolas", 12, "bold")).pack(side="left")
        self.btn_power = tk.Button(hdr, text="⏻ POWER", bg=ROSE, fg="#ffffff", font=("Consolas", 9, "bold"), padx=8, command=self._toggle_power)
        self.btn_power.pack(side="right")

        # 2. Mode Selector Bar (TV / MEDIA / AC / LIGHTS)
        mode_bar = tk.Frame(self.root, bg=BG_DARK, pady=6)
        mode_bar.pack(fill="x")

        for m_name, color in [("TV", CYAN), ("MEDIA", AMBER), ("CLIMATE AC", EMERALD), ("LIGHTS", "#a855f7")]:
            tk.Button(
                mode_bar, text=f"• {m_name}", bg=BG_ACCENT, fg=color, font=("Consolas", 8, "bold"),
                command=lambda m=m_name: self._switch_mode(m)
            ).pack(side="left", fill="x", expand=True, padx=2)

        # 3. Dynamic Control Frame
        self.body_frame = tk.Frame(self.root, bg=BG_DARK, padx=16, pady=4)
        self.body_frame.pack(fill="both", expand=True)

        self._render_tv_controls()

        # 4. Bottom Signal Dispatch Log
        log_card = tk.Frame(self.root, bg=BG_CARD, padx=10, pady=6, height=90)
        log_card.pack(fill="x", side="bottom", padx=8, pady=8)

        tk.Label(log_card, text="TRANSMITTER DISPATCH LEDGER (IR / WI-FI / BLE / ADB):", fg=TEXT_MUTED, bg=BG_CARD, font=("Consolas", 8)).pack(anchor="w")
        self.lbl_log = tk.Label(log_card, text="[IDLE] Standing by for user signal input...", fg=EMERALD, bg=BG_CARD, font=("Consolas", 8), wraplength=420, justify="left")
        self.lbl_log.pack(anchor="w", pady=(2, 0))

    def _switch_mode(self, mode: str):
        self.active_mode = mode
        for widget in self.body_frame.winfo_children():
            widget.destroy()

        if mode == "TV":
            self._render_tv_controls()
        elif mode == "MEDIA":
            self._render_media_controls()
        elif mode == "CLIMATE AC":
            self._render_ac_controls()
        elif mode == "LIGHTS":
            self._render_lights_controls()

        self._log_signal(f"Switched active device profile to: {mode}")

    def _render_tv_controls(self):
        # Quick App Shortcuts (Netflix, YouTube, Prime, Spotify)
        app_f = tk.Frame(self.body_frame, bg=BG_DARK)
        app_f.pack(fill="x", pady=(0, 10))

        tk.Button(app_f, text="NETFLIX", bg="#e50914", fg="#ffffff", font=("Consolas", 8, "bold"), command=lambda: self._dispatch_tv_app("NETFLIX")).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(app_f, text="YOUTUBE", bg="#ff0000", fg="#ffffff", font=("Consolas", 8, "bold"), command=lambda: self._dispatch_tv_app("YOUTUBE")).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(app_f, text="PRIME", bg="#00a8e1", fg="#ffffff", font=("Consolas", 8, "bold"), command=lambda: self._dispatch_tv_app("PRIME VIDEO")).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(app_f, text="INPUT", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 8), command=lambda: self._log_signal("Switched TV Input: HDMI 1 -> HDMI 2")).pack(side="left", fill="x", expand=True, padx=2)

        # D-Pad Navigation Controller
        dpad_frame = tk.Frame(self.body_frame, bg=BG_CARD, padx=20, pady=16)
        dpad_frame.pack(fill="x", pady=6)

        tk.Button(dpad_frame, text="▲ UP", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 10, "bold"), height=2, command=lambda: self._log_signal("TV DPAD: UP")).pack(fill="x", padx=40)

        mid = tk.Frame(dpad_frame, bg=BG_CARD)
        mid.pack(fill="x", pady=4)
        tk.Button(mid, text="◀ LEFT", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 10, "bold"), width=9, height=2, command=lambda: self._log_signal("TV DPAD: LEFT")).pack(side="left", padx=4)
        tk.Button(mid, text="OK", bg=CYAN, fg="#000000", font=("Consolas", 11, "bold"), width=9, height=2, command=lambda: self._log_signal("TV DPAD: SELECT / OK")).pack(side="left", padx=4, fill="x", expand=True)
        tk.Button(mid, text="RIGHT ▶", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 10, "bold"), width=9, height=2, command=lambda: self._log_signal("TV DPAD: RIGHT")).pack(side="left", padx=4)

        tk.Button(dpad_frame, text="▼ DOWN", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 10, "bold"), height=2, command=lambda: self._log_signal("TV DPAD: DOWN")).pack(fill="x", padx=40)

        # Dual Column: Volume & Channel Sliders / Buttons
        vc_f = tk.Frame(self.body_frame, bg=BG_DARK)
        vc_f.pack(fill="x", pady=8)

        # Volume Block
        v_col = tk.Frame(vc_f, bg=BG_CARD, padx=12, pady=10)
        v_col.pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Label(v_col, text="VOLUME", fg=AMBER, bg=BG_CARD, font=("Consolas", 9, "bold")).pack()
        self.lbl_vol = tk.Label(v_col, text=f"{self.current_volume}%", fg=TEXT_LIGHT, bg=BG_CARD, font=("Consolas", 16, "bold"))
        self.lbl_vol.pack(pady=2)
        tk.Button(v_col, text="VOL +", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9, "bold"), command=self._vol_up).pack(fill="x", pady=1)
        tk.Button(v_col, text="VOL -", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9, "bold"), command=self._vol_down).pack(fill="x", pady=1)
        tk.Button(v_col, text="🔇 MUTE", bg=BG_ACCENT, fg=ROSE, font=("Consolas", 8), command=lambda: self._log_signal("Audio Muted")).pack(fill="x", pady=2)

        # Channel Block
        c_col = tk.Frame(vc_f, bg=BG_CARD, padx=12, pady=10)
        c_col.pack(side="right", fill="both", expand=True, padx=(4, 0))
        tk.Label(c_col, text="CHANNEL", fg=EMERALD, bg=BG_CARD, font=("Consolas", 9, "bold")).pack()
        self.lbl_ch = tk.Label(c_col, text=f"CH {self.current_channel}", fg=TEXT_LIGHT, bg=BG_CARD, font=("Consolas", 16, "bold"))
        self.lbl_ch.pack(pady=2)
        tk.Button(c_col, text="CH ▲", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9, "bold"), command=self._ch_up).pack(fill="x", pady=1)
        tk.Button(c_col, text="CH ▼", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9, "bold"), command=self._ch_down).pack(fill="x", pady=1)
        tk.Button(c_col, text="🏠 HOME", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 8), command=lambda: self._log_signal("Returned to TV Home Screen")).pack(fill="x", pady=2)

    def _render_media_controls(self):
        m_card = tk.Frame(self.body_frame, bg=BG_CARD, padx=16, pady=20)
        m_card.pack(fill="both", expand=True)

        tk.Label(m_card, text="STREAMING & AUDIO SOUNDBAR CONTROL", fg=AMBER, bg=BG_CARD, font=("Consolas", 10, "bold")).pack(pady=(0, 14))

        tk.Button(m_card, text="⏯ PLAY / PAUSE", bg=AMBER, fg="#000000", font=("Consolas", 12, "bold"), height=2, command=lambda: self._log_signal("Media: Toggled Play / Pause")).pack(fill="x", pady=4)

        row1 = tk.Frame(m_card, bg=BG_CARD)
        row1.pack(fill="x", pady=4)
        tk.Button(row1, text="⏮ PREV TRACK", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9), command=lambda: self._log_signal("Media: Previous Track")).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(row1, text="NEXT TRACK ⏭", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 9), command=lambda: self._log_signal("Media: Next Track")).pack(side="left", fill="x", expand=True, padx=2)

        tk.Label(m_card, text="EQUALIZER PRESETS:", fg=TEXT_MUTED, bg=BG_CARD, font=("Consolas", 8)).pack(anchor="w", pady=(12, 4))
        for eq in ["DYNAMIC BASS BOOST", "CINEMA SURROUND 7.1", "CLEAR VOICE ENHANCER"]:
            tk.Button(m_card, text=f"🎵 {eq}", bg=BG_ACCENT, fg=CYAN, font=("Consolas", 8), command=lambda e=eq: self._log_signal(f"Soundbar EQ Preset Applied: {e}")).pack(fill="x", pady=2)

    def _render_ac_controls(self):
        ac_card = tk.Frame(self.body_frame, bg=BG_CARD, padx=16, pady=20)
        ac_card.pack(fill="both", expand=True)

        tk.Label(ac_card, text="AIR CONDITIONING & CLIMATE CONTROL", fg=EMERALD, bg=BG_CARD, font=("Consolas", 10, "bold")).pack(pady=(0, 10))

        self.lbl_temp = tk.Label(ac_card, text=f"{self.ac_temp}°C", fg=CYAN, bg=BG_CARD, font=("Consolas", 42, "bold"))
        self.lbl_temp.pack(pady=6)

        t_row = tk.Frame(ac_card, bg=BG_CARD)
        t_row.pack(fill="x", pady=6)
        tk.Button(t_row, text="TEMP -", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 11, "bold"), command=self._temp_down).pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(t_row, text="TEMP +", bg=BG_ACCENT, fg=TEXT_LIGHT, font=("Consolas", 11, "bold"), command=self._temp_up).pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(ac_card, text="OPERATION MODES:", fg=TEXT_MUTED, bg=BG_CARD, font=("Consolas", 8)).pack(anchor="w", pady=(10, 4))
        for mode in ["COOL (TURBO)", "ECO SAVINGS", "AUTO SENSOR", "DEHUMIDIFIER DRY"]:
            tk.Button(ac_card, text=f"❄️ {mode}", bg=BG_ACCENT, fg=EMERALD, font=("Consolas", 8), command=lambda m=mode: self._log_signal(f"AC Climate Mode: {m}")).pack(fill="x", pady=2)

    def _render_lights_controls(self):
        l_card = tk.Frame(self.body_frame, bg=BG_CARD, padx=16, pady=20)
        l_card.pack(fill="both", expand=True)

        tk.Label(l_card, text="SMART HOME RGB LIGHTING", fg="#a855f7", bg=BG_CARD, font=("Consolas", 10, "bold")).pack(pady=(0, 10))

        for name, hex_c in [("ARCTIC CYAN", "#00f0ff"), ("AMBER WARMTH", "#f59e0b"), ("CYBER MATRIX", "#10b981"), ("NEON PURPLE", "#c084fc")]:
            tk.Button(l_card, text=f"💡 MOOD: {name}", bg=BG_ACCENT, fg=hex_c, font=("Consolas", 9, "bold"), command=lambda n=name: self._log_signal(f"Smart Lights Mood Set: {n}")).pack(fill="x", pady=4)

    def _vol_up(self):
        self.current_volume = min(100, self.current_volume + 2)
        try:
            if hasattr(self, "lbl_vol") and self.lbl_vol.winfo_exists():
                self.lbl_vol.config(text=f"{self.current_volume}%")
        except Exception:
            pass
        self._log_signal(f"TV Volume Increased -> {self.current_volume}%")

    def _vol_down(self):
        self.current_volume = max(0, self.current_volume - 2)
        try:
            if hasattr(self, "lbl_vol") and self.lbl_vol.winfo_exists():
                self.lbl_vol.config(text=f"{self.current_volume}%")
        except Exception:
            pass
        self._log_signal(f"TV Volume Decreased -> {self.current_volume}%")

    def _ch_up(self):
        self.current_channel += 1
        try:
            if hasattr(self, "lbl_ch") and self.lbl_ch.winfo_exists():
                self.lbl_ch.config(text=f"CH {self.current_channel}")
        except Exception:
            pass
        self._log_signal(f"Channel Switched Up -> CH {self.current_channel}")

    def _ch_down(self):
        self.current_channel = max(1, self.current_channel - 1)
        try:
            if hasattr(self, "lbl_ch") and self.lbl_ch.winfo_exists():
                self.lbl_ch.config(text=f"CH {self.current_channel}")
        except Exception:
            pass
        self._log_signal(f"Channel Switched Down -> CH {self.current_channel}")

    def _temp_up(self):
        self.ac_temp = min(30, self.ac_temp + 1)
        try:
            if hasattr(self, "lbl_temp") and self.lbl_temp.winfo_exists():
                self.lbl_temp.config(text=f"{self.ac_temp}°C")
        except Exception:
            pass
        self._log_signal(f"AC Temperature Raised -> {self.ac_temp}°C")

    def _temp_down(self):
        self.ac_temp = max(16, self.ac_temp - 1)
        try:
            if hasattr(self, "lbl_temp") and self.lbl_temp.winfo_exists():
                self.lbl_temp.config(text=f"{self.ac_temp}°C")
        except Exception:
            pass
        self._log_signal(f"AC Temperature Lowered -> {self.ac_temp}°C")

    def _dispatch_tv_app(self, app_name: str):
        self._log_signal(f"Dispatched IR/Wi-Fi App Launch Signal -> {app_name}")

    def _toggle_power(self):
        self.power_state = not self.power_state
        state_str = "ON" if self.power_state else "OFF"
        self._log_signal(f"Master Device Power Signal -> {state_str}")

    def _log_signal(self, text: str):
        t_stamp = time.strftime("%H:%M:%S")
        self.lbl_log.config(text=f"[{t_stamp}] {text}")


def launch_universal_remote():
    root = tk.Tk()
    app = UniversalRemoteApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_universal_remote()
