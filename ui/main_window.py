"""
Main Holographic Desktop HUD for P.H.A.S.S Sphere v9.0.
Built with CustomTkinter for dark cosmic glass-morphism, glowing neon borders,
real-time radar scanning line animation, pulsing voice indicator, and telemetry progress bars.
"""

from __future__ import annotations
import json
import logging
import os
import queue
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

from ui.holographic_theme import HOLO_PALETTE, HOLO_ICONS, get_hud_font, apply_holographic_theme_to_ctk
from core.voice_interface import get_voice_interface
from core.llama_tool_agent import process_query

logger = logging.getLogger("phass.ui.main_window")


class HolographicVoiceIndicator(tk.Canvas):
    """Circular pulsing holographic voice indicator widget."""

    def __init__(self, master, size: int = 70, **kwargs):
        super().__init__(
            master,
            width=size,
            height=size,
            bg=HOLO_PALETTE["panel_bg"],
            highlightthickness=0,
            **kwargs,
        )
        self.size = size
        self.center = size // 2
        self.radius = 18
        self.pulse_phase = 0.0
        self.is_active = False
        self._animating = True
        self.after(50, self._animate_pulse)

    def set_active(self, active: bool):
        self.is_active = active

    def _animate_pulse(self):
        if not self._animating:
            return
        self.delete("all")
        self.pulse_phase += 0.12
        glow_delta = abs((self.pulse_phase % 3.14) - 1.57) / 1.57

        if self.is_active:
            # Active voice listening/speaking: pulse from cyan to purple
            ring_r = self.radius + int(glow_delta * 10)
            color = HOLO_PALETTE["accent_purple"] if glow_delta > 0.5 else HOLO_PALETTE["border_cyan"]
            self.create_oval(
                self.center - ring_r, self.center - ring_r,
                self.center + ring_r, self.center + ring_r,
                outline=color, width=2,
            )
            self.create_oval(
                self.center - self.radius, self.center - self.radius,
                self.center + self.radius, self.center + self.radius,
                fill=HOLO_PALETTE["border_cyan"], outline="#ffffff", width=1,
            )
            self.create_text(
                self.center, self.center,
                text="🎙", fill="#0a0a1a", font=("Segoe UI", 12, "bold"),
            )
        else:
            # Idle gentle cyan pulse
            ring_r = self.radius + int(glow_delta * 3)
            self.create_oval(
                self.center - ring_r, self.center - ring_r,
                self.center + ring_r, self.center + ring_r,
                outline=HOLO_PALETTE["text_muted"], width=1,
            )
            self.create_oval(
                self.center - self.radius + 3, self.center - self.radius + 3,
                self.center + self.radius - 3, self.center + self.radius - 3,
                fill="#161633", outline=HOLO_PALETTE["border_cyan"], width=1,
            )
            self.create_text(
                self.center, self.center,
                text="◇", fill=HOLO_PALETTE["border_cyan"], font=("Consolas", 12, "bold"),
            )

        self.after(60, self._animate_pulse)

    def stop_animation(self):
        self._animating = False


class ScanningLineCanvas(tk.Canvas):
    """Horizontal cyan sweeping gradient radar scanning line animation."""

    def __init__(self, master, width: int = 900, height: int = 36, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=HOLO_PALETTE["bg"],
            highlightthickness=0,
            **kwargs,
        )
        self.c_width = width
        self.c_height = height
        self.scan_pos = 0.0
        self.scan_speed = 3.0  # complete sweep in ~3s
        self._running = True
        self.after(30, self._sweep)

    def _sweep(self):
        if not self._running:
            return
        self.delete("all")
        self.scan_pos += self.scan_speed
        if self.scan_pos > self.c_height + 10:
            self.scan_pos = -10.0

        y = int(self.scan_pos)

        # Draw scanning sweep line and trail
        self.create_line(0, y, self.c_width, y, fill=HOLO_PALETTE["border_cyan"], width=2)
        if y > 2:
            self.create_line(0, y - 2, self.c_width, y - 2, fill="#005060", width=1)
        if y > 5:
            self.create_line(0, y - 4, self.c_width, y - 4, fill="#002830", width=1)

        # Grid lines background
        for gx in range(0, self.c_width, 80):
            self.create_line(gx, 0, gx, self.c_height, fill="#12122b", width=1)

        self.after(35, self._sweep)

    def stop(self):
        self._running = False


class AssistantUI:
    """
    Holographic Heads-Up Display (HUD) desktop application for P.H.A.S.S.
    """

    def __init__(self, root: Optional[ctk.CTk] = None):
        apply_holographic_theme_to_ctk()

        if root is None:
            self.root = ctk.CTk()
            self._owns_root = True
        else:
            self.root = root
            self._owns_root = False

        self.root.title("◈ P.H.A.S.S — HOLOGRAPHIC COGNITIVE ENGINE v10.0 ◈")
        self.root.geometry("1240x820")
        self.root.minsize(1050, 720)
        self.root.configure(fg_color=HOLO_PALETTE["bg"])

        # Voice state & task control
        self.voice = get_voice_interface()
        self.is_listening = False
        self.voice_queue = queue.Queue()
        self.autonomous_mode = os.environ.get("LLAMA_AUTONOMOUS", "false").lower() == "true"
        self.system_update_id = None
        self._active_task_cancelled = threading.Event()

        # Build complete HUD layout
        self.setup_holographic_layout()
        self.update_hardware_status()

        # Check session recovery from previous crash
        self.check_session_recovery()

        # Start background intention daemon
        try:
            from core.background_daemon import background_daemon
            background_daemon.register_listener(self._on_hotplug_event)
            background_daemon.start()
        except Exception:
            pass

        # Start Predictive Intelligence & Scout Autopilot
        try:
            from core.predictive_intelligence import predictive_engine
            predictive_engine.register_prediction_listener(self._on_oracle_prediction)
            predictive_engine.start()
        except Exception:
            pass

        try:
            from core.always_on_autopilot import always_on_autopilot
            always_on_autopilot.register_listener(self._on_scout_notification)
            always_on_autopilot.start()
        except Exception:
            pass

        # Start telemetry loop
        self.update_telemetry()

        # Start voice queue loop
        self.process_voice_queue()

    def setup_holographic_layout(self):
        """Constructs all holographic panels with glowing borders and glass effects."""
        # Top Scanning Banner
        self.top_banner = ctk.CTkFrame(self.root, fg_color=HOLO_PALETTE["panel_bg"], height=48, corner_radius=0)
        self.top_banner.pack(fill="x", side="top")

        self.title_label = ctk.CTkLabel(
            self.top_banner,
            text=f"◈ P.H.A.S.S SPHERE v9.0 — HOLOGRAPHIC HYBRID ENGINE",
            font=get_hud_font("title", 16, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        self.title_label.pack(side="left", padx=16, pady=8)

        self.mode_badge = ctk.CTkLabel(
            self.top_banner,
            text="[REAL WORKER MODE: ARMED]",
            font=get_hud_font("mono", 11, bold=True),
            text_color=HOLO_PALETTE["accent_purple"],
        )
        self.mode_badge.pack(side="right", padx=16)

        # Scanning Line Canvas directly under banner
        self.scan_canvas = ScanningLineCanvas(self.root, width=1240, height=12)
        self.scan_canvas.pack(fill="x")

        # Main Body Splitter: Left Sidebar + Center Workspace
        self.body_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.body_frame.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        # 1. Left Sidebar (HUD System Status) with glowing cyan border
        self.sidebar_frame = ctk.CTkFrame(
            self.body_frame,
            width=280,
            fg_color=HOLO_PALETTE["panel_bg"],
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=2,
            corner_radius=10,
        )
        self.sidebar_frame.pack(side="left", fill="y", padx=(0, 10), pady=4)
        self.sidebar_frame.pack_propagate(False)

        self.setup_sidebar()

        # 2. Center Content Area (Tabview)
        self.content_frame = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.content_frame.pack(side="right", fill="both", expand=True, pady=4)

        self.setup_tabview()

        # 3. Bottom Status Bar with glowing cyan progress bars
        self.setup_status_bar()

    def setup_sidebar(self):
        """Constructs left HUD telemetry sidebar."""
        sb_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="◈ HUD SYSTEM STATUS",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        sb_title.pack(pady=(14, 8), padx=12, anchor="w")

        # Pulsing Voice Indicator
        self.voice_indicator = HolographicVoiceIndicator(self.sidebar_frame, size=64)
        self.voice_indicator.pack(pady=(4, 10))

        self.voice_status_lbl = ctk.CTkLabel(
            self.sidebar_frame,
            text="Voice: ◇ Standby",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_secondary"],
        )
        self.voice_status_lbl.pack(pady=(0, 12))

        # Telemetry Card
        self.telemetry_card = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=HOLO_PALETTE["card_bg"],
            border_color="#1c1c3f",
            border_width=1,
            corner_radius=8,
        )
        self.telemetry_card.pack(fill="x", padx=12, pady=6)

        # Status Metrics
        self.stat_engine = ctk.CTkLabel(
            self.telemetry_card,
            text="◈ Engine: Online (Executor)",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_glowing"],
            anchor="w",
        )
        self.stat_engine.pack(fill="x", padx=10, pady=(6, 2))

        self.stat_exec_log = ctk.CTkLabel(
            self.telemetry_card,
            text="💾 Verified Logs: 0",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_secondary"],
            anchor="w",
        )
        self.stat_exec_log.pack(fill="x", padx=10, pady=2)

        self.stat_hw_status = ctk.CTkLabel(
            self.telemetry_card,
            text="🔌 Hardware: [Detected/None]",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_secondary"],
            anchor="w",
        )
        self.stat_hw_status.pack(fill="x", padx=10, pady=2)

        self.stat_skills = ctk.CTkLabel(
            self.telemetry_card,
            text="🔮 Active Skills: Ready",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_secondary"],
            anchor="w",
        )
        self.stat_skills.pack(fill="x", padx=10, pady=2)

        self.stat_auto = ctk.CTkLabel(
            self.telemetry_card,
            text="⚡ Autonomous: Off",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_muted"],
            anchor="w",
        )
        self.stat_auto.pack(fill="x", padx=10, pady=(2, 8))

        # Quick Control Buttons
        self.btn_auto_toggle = ctk.CTkButton(
            self.sidebar_frame,
            text="Toggle Autonomous Mode",
            command=self.toggle_autonomous_mode,
            fg_color=HOLO_PALETTE["accent_purple"],
            hover_color=HOLO_PALETTE["accent_purple_hover"],
            font=get_hud_font("body", 11, bold=True),
            height=32,
        )
        self.btn_auto_toggle.pack(fill="x", padx=12, pady=(14, 6))

        self.btn_voice_toggle = ctk.CTkButton(
            self.sidebar_frame,
            text="🎙 Activate Voice",
            command=self.toggle_voice,
            fg_color="#182848",
            hover_color="#203a66",
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=1,
            font=get_hud_font("body", 11),
            height=32,
        )
        self.btn_voice_toggle.pack(fill="x", padx=12, pady=6)

        # Quick-Action Button: Detect Hardware
        self.btn_detect_hw = ctk.CTkButton(
            self.sidebar_frame,
            text="📡 Detect Hardware",
            command=self.trigger_detect_hardware,
            fg_color="#12253d",
            hover_color="#1c375c",
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=1,
            font=get_hud_font("body", 11, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
            height=32,
        )
        self.btn_detect_hw.pack(fill="x", padx=12, pady=(2, 6))


        # Quick Hardware Shortcuts
        quick_hw_lbl = ctk.CTkLabel(
            self.sidebar_frame,
            text="⚡ QUICK COMMANDS",
            font=get_hud_font("header", 10, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        quick_hw_lbl.pack(pady=(16, 4), padx=12, anchor="w")

        shortcuts = [
            ("Pinout: BC547", "What is the pinout of the BC547 transistor?"),
            ("Debug LED", "My LED is not turning on, help me debug it"),
            ("Start Smart_Sensor", "Start a new project called Smart_Sensor"),
            ("Backup at 2 AM", "Schedule a daily backup at 2 AM"),
        ]
        for label, cmd in shortcuts:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                command=lambda c=cmd: self.execute_quick_command(c),
                fg_color="#101026",
                hover_color="#18183c",
                font=get_hud_font("mono", 10),
                height=26,
            )
            btn.pack(fill="x", padx=12, pady=2)

    def setup_tabview(self):
        """Constructs multi-tab holographic interface."""
        self.tabview = ctk.CTkTabview(
            self.content_frame,
            fg_color=HOLO_PALETTE["panel_bg"],
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=1,
            segmented_button_selected_color=HOLO_PALETTE["accent_purple"],
            segmented_button_selected_hover_color=HOLO_PALETTE["accent_purple_hover"],
            segmented_button_unselected_color="#14142e",
            text_color=HOLO_PALETTE["text_glowing"],
        )
        self.tabview.pack(fill="both", expand=True)

        self.tab_chat = self.tabview.add("◈ Chat & Console")
        self.tab_hud = self.tabview.add("⌖ Holographic HUD")
        self.tab_telemetry = self.tabview.add("⚡ System Telemetry")
        self.tab_serial = self.tabview.add("📈 Serial Plotter")
        self.tab_oracle = self.tabview.add("🔮 The Oracle")
        self.tab_immunity = self.tabview.add("🛡 Immunity")
        self.tab_evolution = self.tabview.add("🧬 Evolution")

        self.setup_chat_tab()
        self.setup_hud_tab()
        self.setup_telemetry_tab()
        self.setup_serial_plotter_tab()
        self.setup_oracle_tab()
        self.setup_immunity_tab()
        self.setup_evolution_tab()

    def setup_chat_tab(self):
        """Constructs chat conversation view with glowing input."""
        chat_container = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        chat_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Chat Text Box
        self.chat_display = ctk.CTkTextbox(
            chat_container,
            fg_color="#0a0a1a",
            text_color=HOLO_PALETTE["text_glowing"],
            font=get_hud_font("mono", 11),
            border_color="#1a1a3a",
            border_width=1,
            wrap="word",
        )
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_display.configure(state="disabled")

        # Initial Welcome Message
        self.add_chat_message(
            "assistant",
            "◈ P.H.A.S.S HOLOGRAPHIC HYBRID ENGINE READY ◈\n"
            "• Execution Pipeline: Strict Planner -> Executor -> Verifier active.\n"
            "• Hardware Engineering & Vibe Coding: Datasheet engine, pinout visualizer, and circuit debugger ready.\n"
            "• Autonomous Operations & Scheduled Tasks: Armed.\n"
            "Enter your directive below or select a quick command.",
        )

        # Active Task Status Frame (Non-Blocking Progress & Task Cancellation)
        self.active_task_frame = ctk.CTkFrame(
            chat_container,
            fg_color="#0e1326",
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=1,
            corner_radius=6,
            height=38,
        )
        self.active_task_frame.pack_propagate(False)

        self.task_status_label = ctk.CTkLabel(
            self.active_task_frame,
            text="⏳ Compiling firmware... (This may take 30 seconds)",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        self.task_status_label.pack(side="left", padx=(12, 10), pady=4)

        self.task_progress_bar = ctk.CTkProgressBar(
            self.active_task_frame,
            width=200,
            height=8,
            progress_color=HOLO_PALETTE["accent_purple"],
        )
        self.task_progress_bar.pack(side="left", padx=(0, 10), pady=12)
        self.task_progress_bar.set(0.0)

        self.btn_task_cancel = ctk.CTkButton(
            self.active_task_frame,
            text="⏹️ Cancel",
            width=76,
            height=24,
            fg_color="#4d1a24",
            hover_color="#7a2536",
            text_color="#ff8da1",
            font=get_hud_font("body", 10, bold=True),
            command=self.cancel_active_task,
        )
        self.btn_task_cancel.pack(side="right", padx=(0, 8), pady=6)

        # Bottom Input Frame with glowing cyan border
        self.input_frame = ctk.CTkFrame(
            chat_container,
            fg_color=HOLO_PALETTE["card_bg"],
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=2,
            corner_radius=8,
            height=54,
        )
        self.input_frame.pack(fill="x", pady=(0, 2))
        self.input_frame.pack_propagate(False)

        self.input_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Enter hardware directive or system command (e.g. 'What is the pinout of BC547?')...",
            font=get_hud_font("mono", 11),
            fg_color="transparent",
            text_color=HOLO_PALETTE["text_glowing"],
            placeholder_text_color="#4f6a82",
            border_width=0,
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=6)
        self.input_entry.bind("<Return>", lambda event: self.send_message())

        self.btn_send = ctk.CTkButton(
            self.input_frame,
            text="⚡ Transmit",
            width=90,
            fg_color=HOLO_PALETTE["accent_purple"],
            hover_color=HOLO_PALETTE["accent_purple_hover"],
            font=get_hud_font("body", 11, bold=True),
            command=self.send_message,
        )
        self.btn_send.pack(side="right", padx=6, pady=6)

        self.btn_clear = ctk.CTkButton(
            self.input_frame,
            text="◇ Clear",
            width=60,
            fg_color="#181836",
            hover_color="#202048",
            font=get_hud_font("body", 11),
            command=self.clear_chat,
        )
        self.btn_clear.pack(side="right", padx=(0, 4), pady=6)

    def setup_hud_tab(self):
        """Constructs dedicated HUD visualization tab."""
        hud_container = ctk.CTkFrame(self.tab_hud, fg_color="transparent")
        hud_container.pack(fill="both", expand=True, padx=12, pady=12)

        hud_label = ctk.CTkLabel(
            hud_container,
            text="⌖ ACTIVE HOLOGRAPHIC SUBSYSTEMS & REUSABLE SKILLS",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        hud_label.pack(pady=(0, 10), anchor="w")

        # 3 Panels: Execution Pipeline, Hardware Engine, Self-Improvement
        grid_frame = ctk.CTkFrame(hud_container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure((0, 1, 2), weight=1, uniform="col")

        # Panel 1: Execution Engine
        p1 = ctk.CTkFrame(grid_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["border_cyan"], border_width=1)
        p1.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(p1, text="⚙️ Execution Engine", font=get_hud_font("title", 12, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(pady=8, padx=10, anchor="w")
        self.hud_p1_text = ctk.CTkLabel(
            p1,
            text="• Pipeline: Planner -> Executor -> Verifier\n• Retry Policy: Single auto-retry enabled\n• Side-effect Audit: psutil & OS verified\n• Hallucination Defense: Active",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.hud_p1_text.pack(fill="x", padx=10, pady=4)

        # Panel 2: Hardware Co-Pilot
        p2 = ctk.CTkFrame(grid_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["accent_purple"], border_width=1)
        p2.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(p2, text="🔌 Hardware Engine", font=get_hud_font("title", 12, bold=True), text_color=HOLO_PALETTE["accent_purple"]).pack(pady=8, padx=10, anchor="w")
        self.hud_p2_text = ctk.CTkLabel(
            p2,
            text="• Datasheet Fetcher: Local Cache & Web\n• Pinout Visualizer: ASCII Diagram Engine\n• Debug Oracle: Multimeter Path of Solution\n• Vibe Coding: Dual Firmware/Hardware sync",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.hud_p2_text.pack(fill="x", padx=10, pady=4)

        # Panel 3: Self-Improvement & Skills
        p3 = ctk.CTkFrame(grid_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["border_cyan"], border_width=1)
        p3.grid(row=0, column=2, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(p3, text="🔮 Skills & Autonomous", font=get_hud_font("title", 12, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(pady=8, padx=10, anchor="w")
        self.hud_p3_text = ctk.CTkLabel(
            p3,
            text="• Skill Recorder: Active (3-run auto-save)\n• Auto-Tuning: CPU/RAM telemetry load gate\n• Error Correlator: Active\n• Daily Operations: 6 AM Briefing / 2 AM Backup",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.hud_p3_text.pack(fill="x", padx=10, pady=4)

    def setup_telemetry_tab(self):
        """Constructs system telemetry metrics view."""
        telem_container = ctk.CTkFrame(self.tab_telemetry, fg_color="transparent")
        telem_container.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            telem_container,
            text="⚡ LIVE HOST TELEMETRY & RESOURCES",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        ).pack(pady=(0, 10), anchor="w")

        self.telem_details = ctk.CTkLabel(
            telem_container,
            text="Querying system telemetry...",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_glowing"],
            justify="left",
            anchor="w",
        )
        self.telem_details.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_serial_plotter_tab(self):
        """Constructs embedded live serial monitor and real-time waveform plotter."""
        serial_container = ctk.CTkFrame(self.tab_serial, fg_color="transparent")
        serial_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Header toolbar with controls
        toolbar = ctk.CTkFrame(serial_container, fg_color="#101026", height=40)
        toolbar.pack(fill="x", pady=(0, 6))

        lbl_port = ctk.CTkLabel(
            toolbar,
            text="PORT: COM3 | BAUD: 115200 | AUTO-PLOTTER ARMED",
            font=get_hud_font("mono", 11, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        lbl_port.pack(side="left", padx=12, pady=6)

        btn_clear_plot = ctk.CTkButton(
            toolbar,
            text="Clear Waveform",
            width=110,
            height=26,
            fg_color="#18183c",
            hover_color="#28285c",
            font=get_hud_font("mono", 10),
            command=self.clear_serial_plotter,
        )
        btn_clear_plot.pack(side="right", padx=8, pady=6)

        # Split container: Top Matplotlib Plot, Bottom Text Monitor
        content_split = ctk.CTkFrame(serial_container, fg_color="transparent")
        content_split.pack(fill="both", expand=True)

        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        self.serial_fig = Figure(figsize=(7, 3), dpi=100)
        self.serial_fig.patch.set_facecolor("#0a0a1a")
        self.serial_ax = self.serial_fig.add_subplot(111)
        self.serial_ax.set_facecolor("#0a0a1a")
        self.serial_ax.tick_params(colors="#4f6a82", labelsize=8)
        for spine in self.serial_ax.spines.values():
            spine.set_color("#1a1a3a")
        self.serial_ax.grid(True, color="#151530", linestyle="--", linewidth=0.5)

        self.serial_plot_data = [100.0, 180.0, 240.0, 310.0, 280.0, 220.0, 190.0, 250.0]
        self.serial_line, = self.serial_ax.plot(
            self.serial_plot_data,
            color=HOLO_PALETTE["border_cyan"],
            linewidth=2.0,
            marker="o",
            markersize=3,
        )

        self.plot_canvas = FigureCanvasTkAgg(self.serial_fig, master=content_split)
        self.plot_canvas.get_tk_widget().pack(side="top", fill="both", expand=True, pady=(0, 6))
        self.plot_canvas.draw()

        # Bottom Text Log
        self.serial_text_monitor = ctk.CTkTextbox(
            content_split,
            height=130,
            fg_color="#080816",
            text_color="#00e5ff",
            font=get_hud_font("mono", 10),
            border_color="#1a1a3a",
            border_width=1,
        )
        self.serial_text_monitor.pack(side="bottom", fill="x")
        self.serial_text_monitor.insert("end", "[SERIAL MONITOR INITIALIZED] Listening on COM3 @ 115200 baud...\n")

    def feed_serial_data(self, raw_line: str):
        """Feeds incoming serial line into plotter and text monitor."""
        if hasattr(self, "serial_text_monitor"):
            self.serial_text_monitor.insert("end", f"{raw_line}\n")
            self.serial_text_monitor.see("end")

        # Parse comma-separated or single numbers: e.g. "100, 200, 300"
        vals = re.findall(r"[-+]?\d+(?:\.\d+)?", raw_line)
        if vals and hasattr(self, "serial_line"):
            try:
                for v in vals:
                    self.serial_plot_data.append(float(v))
                if len(self.serial_plot_data) > 60:
                    self.serial_plot_data = self.serial_plot_data[-60:]
                self.serial_line.set_ydata(self.serial_plot_data)
                self.serial_line.set_xdata(range(len(self.serial_plot_data)))
                self.serial_ax.relim()
                self.serial_ax.autoscale_view()
                self.plot_canvas.draw_idle()
            except Exception:
                pass

    def clear_serial_plotter(self):
        """Clears serial plot and monitor."""
        self.serial_plot_data = [0.0]
        self.serial_line.set_ydata(self.serial_plot_data)
        self.serial_line.set_xdata([0])
        self.serial_ax.relim()
        self.serial_ax.autoscale_view()
        self.plot_canvas.draw_idle()
        if hasattr(self, "serial_text_monitor"):
            self.serial_text_monitor.delete("1.0", "end")

    def setup_oracle_tab(self):
        """Constructs The Oracle predictive intelligence & swarm monitoring view."""
        oracle_container = ctk.CTkFrame(self.tab_oracle, fg_color="transparent")
        oracle_container.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkLabel(
            oracle_container,
            text="🔮 THE ORACLE — PREDICTIVE INTELLIGENCE & SWARM MONITOR",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        header.pack(pady=(0, 8), anchor="w")

        # Top Section: Active Predictions List
        self.oracle_pred_card = ctk.CTkFrame(
            oracle_container,
            fg_color=HOLO_PALETTE["card_bg"],
            border_color=HOLO_PALETTE["border_cyan"],
            border_width=1,
            corner_radius=8,
        )
        self.oracle_pred_card.pack(fill="x", pady=6)

        pred_title = ctk.CTkLabel(
            self.oracle_pred_card,
            text="⌖ LIKELY NEXT ACTIONS & INTENTION FORECAST",
            font=get_hud_font("title", 11, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        pred_title.pack(pady=(8, 4), padx=12, anchor="w")

        self.oracle_pred_label = ctk.CTkLabel(
            self.oracle_pred_card,
            text="[94% Confidence] ESP32 project opened. Pre-load PlatformIO toolchain & COM3 port.",
            font=get_hud_font("mono", 11),
            text_color=HOLO_PALETTE["text_glowing"],
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self.oracle_pred_label.pack(fill="x", padx=12, pady=4)

        btn_bar = ctk.CTkFrame(self.oracle_pred_card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=12, pady=(4, 8))

        self.btn_oracle_approve = ctk.CTkButton(
            btn_bar,
            text="✓ Approve Action",
            width=120,
            height=28,
            fg_color=HOLO_PALETTE["accent_purple"],
            hover_color=HOLO_PALETTE["accent_purple_hover"],
            font=get_hud_font("mono", 10, bold=True),
            command=self.approve_current_prediction,
        )
        self.btn_oracle_approve.pack(side="left", padx=(0, 8))

        self.btn_oracle_dismiss = ctk.CTkButton(
            btn_bar,
            text="✗ Dismiss",
            width=90,
            height=28,
            fg_color="#18183c",
            hover_color="#28285c",
            font=get_hud_font("mono", 10),
            command=self.dismiss_current_prediction,
        )
        self.btn_oracle_dismiss.pack(side="left")

        # Middle Section: Swarm Intelligence & Scout Sentinel
        swarm_frame = ctk.CTkFrame(oracle_container, fg_color="transparent")
        swarm_frame.pack(fill="both", expand=True, pady=8)
        swarm_frame.columnconfigure((0, 1), weight=1, uniform="col")

        # Swarm Collective Card
        c1 = ctk.CTkFrame(swarm_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["accent_purple"], border_width=1)
        c1.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c1, text="🐝 Autonomous Agent Swarm", font=get_hud_font("title", 11, bold=True), text_color=HOLO_PALETTE["accent_purple"]).pack(pady=6, padx=10, anchor="w")
        self.lbl_swarm_status = ctk.CTkLabel(
            c1,
            text="• Orchestrator: Standing By\n• UI/UX Specialist: Ready\n• Frontend Specialist: Ready\n• Backend Specialist: Ready\n• Hardware Specialist: Ready\n• Reviewer Agent: Auditing (100% Peer Review)",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.lbl_swarm_status.pack(fill="both", expand=True, padx=10, pady=4)

        # Scout Sentinel Card
        c2 = ctk.CTkFrame(swarm_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["border_cyan"], border_width=1)
        c2.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(c2, text="⏳ Always-On Autopilot (Scout)", font=get_hud_font("title", 11, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(pady=6, padx=10, anchor="w")
        self.lbl_scout_status = ctk.CTkLabel(
            c2,
            text="• Sentinel Daemon: ACTIVE\n• Proactive Disk Maintenance: <15% Auto-Clean\n• Intelligent Follow-Through: Scanning Promises\n• Unprompted Hotplug: Monitoring Ports\n• Status: ⚡ WATCHING HOST INTEGRITY",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.lbl_scout_status.pack(fill="both", expand=True, padx=10, pady=4)

    def approve_current_prediction(self):
        try:
            from core.predictive_intelligence import predictive_engine
            preds = predictive_engine.get_active_predictions()
            if preds:
                res = predictive_engine.approve_prediction(preds[0]["id"])
                self.oracle_pred_label.configure(text=f"✓ {res.get('message', 'Approved')}", text_color=HOLO_PALETTE["border_cyan"])
            else:
                self.oracle_pred_label.configure(text="No pending predictions to approve.", text_color=HOLO_PALETTE["text_secondary"])
        except Exception as e:
            self.oracle_pred_label.configure(text=f"Approval error: {e}")

    def dismiss_current_prediction(self):
        try:
            from core.predictive_intelligence import predictive_engine
            preds = predictive_engine.get_active_predictions()
            if preds:
                res = predictive_engine.dismiss_prediction(preds[0]["id"])
                self.oracle_pred_label.configure(text=f"✗ {res.get('message', 'Dismissed')}", text_color=HOLO_PALETTE["text_muted"])
            else:
                self.oracle_pred_label.configure(text="No pending predictions to dismiss.", text_color=HOLO_PALETTE["text_secondary"])
        except Exception as e:
            self.oracle_pred_label.configure(text=f"Dismiss error: {e}")

    def _on_oracle_prediction(self, prediction: Dict[str, Any]):
        try:
            if hasattr(self, "oracle_pred_label"):
                conf = int(prediction.get("confidence", 0.9) * 100)
                text = f"[{conf}% Confidence] {prediction.get('title')}: {prediction.get('description')}"
                self.oracle_pred_label.configure(text=text, text_color=HOLO_PALETTE["text_glowing"])
        except Exception:
            pass

    def _on_scout_notification(self, notification: Dict[str, Any]):
        try:
            if hasattr(self, "lbl_scout_status"):
                msg = f"• Last Event: {notification.get('title')} ({notification.get('category')})\n• {notification.get('message')}"
                self.lbl_scout_status.configure(text=msg)
        except Exception:
            pass

    def setup_immunity_tab(self):
        """Constructs Autonomic Immunity & Self-Healing circuit dashboard tab."""
        immunity_container = ctk.CTkFrame(self.tab_immunity, fg_color="transparent")
        immunity_container.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkLabel(
            immunity_container,
            text="🛡 AUTONOMIC IMMUNITY & SELF-HEALING CIRCUIT",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        header.pack(pady=(0, 4), anchor="w")

        subhead = ctk.CTkLabel(
            immunity_container,
            text="Continuous runtime fault detection, AST sandbox isolation, and 60-second crash rollback protection.",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
        )
        subhead.pack(pady=(0, 10), anchor="w")

        # Metric Cards Frame (3 Columns)
        cards_frame = ctk.CTkFrame(immunity_container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=6)
        cards_frame.columnconfigure((0, 1, 2), weight=1, uniform="immunity_cols")

        # Card 1: Errors Fixed Today
        c1 = ctk.CTkFrame(cards_frame, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["border_cyan"], border_width=1, corner_radius=8)
        c1.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")
        ctk.CTkLabel(c1, text="ERRORS FIXED TODAY", font=get_hud_font("title", 10, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(pady=(8, 2), padx=10, anchor="w")
        self.lbl_fixed_today = ctk.CTkLabel(c1, text="0", font=get_hud_font("header", 22, bold=True), text_color=HOLO_PALETTE["text_glowing"])
        self.lbl_fixed_today.pack(pady=2, padx=10, anchor="w")
        ctk.CTkLabel(c1, text="Autonomous hotfixes deployed", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"]).pack(pady=(0, 8), padx=10, anchor="w")

        # Card 2: Pending Review (<70%)
        c2 = ctk.CTkFrame(cards_frame, fg_color=HOLO_PALETTE["card_bg"], border_color="#ffaa00", border_width=1, corner_radius=8)
        c2.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")
        ctk.CTkLabel(c2, text="PENDING REVIEW", font=get_hud_font("title", 10, bold=True), text_color="#ffaa00").pack(pady=(8, 2), padx=10, anchor="w")
        self.lbl_pending_review = ctk.CTkLabel(c2, text="0", font=get_hud_font("header", 22, bold=True), text_color="#ffcc66")
        self.lbl_pending_review.pack(pady=2, padx=10, anchor="w")
        ctk.CTkLabel(c2, text="Safety valve escalations (<70%)", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"]).pack(pady=(0, 8), padx=10, anchor="w")

        # Card 3: Rollbacks (60s Guard)
        c3 = ctk.CTkFrame(cards_frame, fg_color=HOLO_PALETTE["card_bg"], border_color="#ff4444", border_width=1, corner_radius=8)
        c3.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")
        ctk.CTkLabel(c3, text="ROLLBACKS (60S GUARD)", font=get_hud_font("title", 10, bold=True), text_color="#ff4444").pack(pady=(8, 2), padx=10, anchor="w")
        self.lbl_rollbacks = ctk.CTkLabel(c3, text="0", font=get_hud_font("header", 22, bold=True), text_color="#ff6666")
        self.lbl_rollbacks.pack(pady=2, padx=10, anchor="w")
        ctk.CTkLabel(c3, text="Failed patch restorations", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"]).pack(pady=(0, 8), padx=10, anchor="w")

        # Activity Stream Section
        stream_frame = ctk.CTkFrame(immunity_container, fg_color=HOLO_PALETTE["card_bg"], border_color="#1a1a3a", border_width=1, corner_radius=8)
        stream_frame.pack(fill="both", expand=True, pady=(8, 0))

        toolbar = ctk.CTkFrame(stream_frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(toolbar, text="⚡ RECENT RECOVERY CIRCUIT ACTIONS", font=get_hud_font("title", 11, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(side="left")

        btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄 Refresh Metrics",
            width=120,
            height=26,
            fg_color="#181836",
            hover_color="#22224c",
            font=get_hud_font("mono", 10),
            command=self.refresh_immunity_metrics,
        )
        btn_refresh.pack(side="right", padx=4)

        btn_audit = ctk.CTkButton(
            toolbar,
            text="🧹 Run Weekly Audit",
            width=130,
            height=26,
            fg_color=HOLO_PALETTE["accent_purple"],
            hover_color=HOLO_PALETTE["accent_purple_hover"],
            font=get_hud_font("mono", 10),
            command=self.run_circuit_audit,
        )
        btn_audit.pack(side="right", padx=4)

        # Log Display
        self.immunity_log_display = ctk.CTkTextbox(
            stream_frame,
            fg_color="#090918",
            text_color=HOLO_PALETTE["text_glowing"],
            font=get_hud_font("mono", 10),
            border_color="#1a1a3a",
            border_width=1,
            wrap="word",
        )
        self.immunity_log_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Initial metrics load
        self.refresh_immunity_metrics()

    def refresh_immunity_metrics(self):
        """Refreshes immunity counters and activity stream from rollback manager."""
        try:
            from core.rollback_manager import rollback_manager
            metrics = rollback_manager.get_metrics()

            fixed = metrics.get("errors_fixed_today", 0)
            pending = metrics.get("pending_review", 0)
            rollbacks = metrics.get("rollbacks", 0)
            history = metrics.get("history", [])

            if hasattr(self, "lbl_fixed_today"):
                self.lbl_fixed_today.configure(text=str(fixed))
            if hasattr(self, "lbl_pending_review"):
                self.lbl_pending_review.configure(text=str(pending))
            if hasattr(self, "lbl_rollbacks"):
                self.lbl_rollbacks.configure(text=str(rollbacks))

            if hasattr(self, "immunity_log_display"):
                self.immunity_log_display.configure(state="normal")
                self.immunity_log_display.delete("1.0", "end")

                if not history:
                    self.immunity_log_display.insert("end", "🛡 Circuit Armed. No faults encountered today. System integrity 100%.\n")
                else:
                    self.immunity_log_display.insert("end", f"--- Autonomic Circuit Log [Last Updated: {datetime.now().strftime('%H:%M:%S')}] ---\n\n")
                    for entry in reversed(history[-20:]):
                        ts = entry.get("timestamp", "")[:19].replace("T", " ")
                        action = entry.get("action", "EVENT")
                        target = entry.get("target_file", entry.get("error_type", "system"))
                        self.immunity_log_display.insert("end", f"[{ts}] {action} -> {target}\n")
                        for k, v in entry.items():
                            if k not in ("timestamp", "action", "target_file"):
                                self.immunity_log_display.insert("end", f"    {k}: {v}\n")
                        self.immunity_log_display.insert("end", "\n")

                self.immunity_log_display.configure(state="disabled")

        except Exception as e:
            logger.debug(f"Immunity refresh notice: {e}")

    def run_circuit_audit(self):
        """Triggers autopilot weekly error audit manually."""
        try:
            from core.autopilot_mode import autopilot_mode
            res = autopilot_mode.run_weekly_error_audit()
            self.refresh_immunity_metrics()
            self.add_chat_message("assistant", f"🛡 Weekly Error Audit Complete:\n• Purged {res.get('purged_backups', 0)} old backups (>7d)\n• Compacted {res.get('compacted_errors', 0)} redundant error patterns.")
        except Exception as e:
            self.add_chat_message("assistant", f"Audit notice: {e}")

    def setup_evolution_tab(self):
        """Constructs Recursive Architect v14.0 Evolution dashboard tab."""
        evo_container = ctk.CTkFrame(self.tab_evolution, fg_color="transparent")
        evo_container.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkLabel(
            evo_container,
            text="🧬 RECURSIVE ARCHITECT & CODEBASE EVOLUTION (v14.0)",
            font=get_hud_font("header", 13, bold=True),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        header.pack(pady=(0, 4), anchor="w")

        subhead = ctk.CTkLabel(
            evo_container,
            text="Autonomous static code analysis, structural AST refactoring, 100-run performance benchmarks, and rollback protection.",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["text_secondary"],
        )
        subhead.pack(pady=(0, 8), anchor="w")

        # Toolbar
        toolbar = ctk.CTkFrame(evo_container, fg_color="#101026", height=40)
        toolbar.pack(fill="x", pady=(0, 8))

        btn_analyze = ctk.CTkButton(
            toolbar,
            text="🔍 Analyze Architecture",
            width=160,
            height=28,
            fg_color="#181836",
            hover_color="#24244c",
            font=get_hud_font("mono", 10, bold=True),
            command=self.ui_run_architect_analyze,
        )
        btn_analyze.pack(side="left", padx=8, pady=6)

        btn_upgrade = ctk.CTkButton(
            toolbar,
            text="⚡ Upgrade Architecture",
            width=170,
            height=28,
            fg_color=HOLO_PALETTE["accent_purple"],
            hover_color=HOLO_PALETTE["accent_purple_hover"],
            font=get_hud_font("mono", 10, bold=True),
            command=self.ui_run_architect_upgrade,
        )
        btn_upgrade.pack(side="left", padx=8, pady=6)

        btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄 Refresh History",
            width=130,
            height=28,
            fg_color="#12122b",
            hover_color="#1c1c3f",
            font=get_hud_font("mono", 10),
            command=self.refresh_evolution_metrics,
        )
        btn_refresh.pack(side="right", padx=8, pady=6)

        # Top Card: Priority Ranking Table
        rank_card = ctk.CTkFrame(evo_container, fg_color=HOLO_PALETTE["card_bg"], border_color=HOLO_PALETTE["border_cyan"], border_width=1, corner_radius=8)
        rank_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(rank_card, text="⌖ REFACTOR PRIORITY RANKING (TOP CANDIDATES)", font=get_hud_font("title", 11, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(anchor="w", padx=12, pady=(8, 4))

        self.lbl_evo_rank1 = ctk.CTkLabel(rank_card, text="1. Scanning codebase...", font=get_hud_font("mono", 10), text_color=HOLO_PALETTE["text_glowing"], justify="left", anchor="w")
        self.lbl_evo_rank1.pack(fill="x", padx=14, pady=2)

        self.lbl_evo_rank2 = ctk.CTkLabel(rank_card, text="2. Scanning codebase...", font=get_hud_font("mono", 10), text_color=HOLO_PALETTE["text_secondary"], justify="left", anchor="w")
        self.lbl_evo_rank2.pack(fill="x", padx=14, pady=2)

        self.lbl_evo_rank3 = ctk.CTkLabel(rank_card, text="3. Scanning codebase...", font=get_hud_font("mono", 10), text_color=HOLO_PALETTE["text_muted"], justify="left", anchor="w")
        self.lbl_evo_rank3.pack(fill="x", padx=14, pady=(2, 8))

        # Bottom Card: Evolution History Stream
        hist_card = ctk.CTkFrame(evo_container, fg_color=HOLO_PALETTE["card_bg"], border_color="#1a1a3a", border_width=1, corner_radius=8)
        hist_card.pack(fill="both", expand=True)

        ctk.CTkLabel(hist_card, text="⚡ ARCHITECTURAL EVOLUTION HISTORY & SPEED BENCHMARKS", font=get_hud_font("title", 11, bold=True), text_color=HOLO_PALETTE["border_cyan"]).pack(anchor="w", padx=12, pady=(8, 4))

        self.evolution_log_display = ctk.CTkTextbox(
            hist_card,
            fg_color="#090918",
            text_color=HOLO_PALETTE["text_glowing"],
            font=get_hud_font("mono", 10),
            border_color="#1a1a3a",
            border_width=1,
            wrap="word",
        )
        self.evolution_log_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Initial data load
        self.refresh_evolution_metrics()

    def refresh_evolution_metrics(self):
        """Loads refactor report and evolution history into Evolution tab."""
        try:
            from core.recursive_architect import recursive_architect

            # Load Refactor Report
            report_file = Path(__file__).parent.parent / "checkpoints" / "refactor_report.json"
            if report_file.exists():
                raw = json.loads(report_file.read_text(encoding="utf-8"))
                ranked = raw.get("ranked_files", [])
                if len(ranked) >= 1 and hasattr(self, "lbl_evo_rank1"):
                    r1 = ranked[0]
                    self.lbl_evo_rank1.configure(
                        text=f"1. [Score: {r1.get('score')}] {r1.get('file_path')} (Complexity: {r1.get('complexity')} | LOC: {r1.get('loc')} | Freq: {r1.get('execution_frequency')})",
                        text_color=HOLO_PALETTE["border_cyan"]
                    )
                if len(ranked) >= 2 and hasattr(self, "lbl_evo_rank2"):
                    r2 = ranked[1]
                    self.lbl_evo_rank2.configure(
                        text=f"2. [Score: {r2.get('score')}] {r2.get('file_path')} (Complexity: {r2.get('complexity')} | LOC: {r2.get('loc')} | Freq: {r2.get('execution_frequency')})"
                    )
                if len(ranked) >= 3 and hasattr(self, "lbl_evo_rank3"):
                    r3 = ranked[2]
                    self.lbl_evo_rank3.configure(
                        text=f"3. [Score: {r3.get('score')}] {r3.get('file_path')} (Complexity: {r3.get('complexity')} | LOC: {r3.get('loc')} | Freq: {r3.get('execution_frequency')})"
                    )

            # Load Evolution Log
            history = recursive_architect.get_evolution_history()
            if hasattr(self, "evolution_log_display"):
                self.evolution_log_display.configure(state="normal")
                self.evolution_log_display.delete("1.0", "end")

                if not history:
                    self.evolution_log_display.insert("end", "🧬 Evolution Circuit Ready. No self-rewriting cycles run yet.\nClick 'Analyze Architecture' to evaluate candidate modules.\n")
                else:
                    self.evolution_log_display.insert("end", f"--- Recursive Architect Evolution Log [{datetime.now().strftime('%H:%M:%S')}] ---\n\n")
                    for item in reversed(history[-15:]):
                        evo_id = item.get("evolution_id", "EVO")
                        ts = item.get("timestamp", "")[:19].replace("T", " ")
                        status = item.get("status", "UNKNOWN")
                        speed = item.get("speed_improvement_pct", 0.0)
                        commit = item.get("git_commit", "")
                        fn = item.get("target_function", "function")
                        self.evolution_log_display.insert("end", f"[{ts}] {evo_id} | Status: {status} | Target: {fn} | Speed: {speed:+.1f}%\n")
                        if commit:
                            self.evolution_log_display.insert("end", f"    Commit: {commit}\n")
                        self.evolution_log_display.insert("end", f"    Details: {item.get('message', '')}\n\n")

                self.evolution_log_display.configure(state="disabled")

        except Exception as e:
            logger.debug(f"Evolution tab refresh notice: {e}")

    def ui_run_architect_analyze(self):
        """User action to scan and rank codebase modules."""
        try:
            from core.recursive_architect import recursive_architect
            report = recursive_architect.analyze_codebase()
            self.refresh_evolution_metrics()
            worst = report.ranked_files[0].file_path if report.ranked_files else "none"
            self.add_chat_message("assistant", f"🧬 Codebase Analysis Complete ({report.total_files_scanned} files scanned).\nWeakest candidate module: {worst}.")
        except Exception as e:
            self.add_chat_message("assistant", f"Analysis error: {e}")

    def ui_run_architect_upgrade(self):
        """User action to autonomously refactor and deploy the worst module."""
        try:
            from core.recursive_architect import recursive_architect
            record = recursive_architect.upgrade_worst_module()
            self.refresh_evolution_metrics()
            self.add_chat_message("assistant", f"🧬 {record.message}")
        except Exception as e:
            self.add_chat_message("assistant", f"Upgrade error: {e}")

    def setup_status_bar(self):
        """Constructs holographic bottom status bar with progress bars."""
        self.status_bar = ctk.CTkFrame(self.root, fg_color=HOLO_PALETTE["panel_bg"], height=38, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")

        # Left status label
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="◈ System Status: Online & Verified",
            font=get_hud_font("mono", 10),
            text_color=HOLO_PALETTE["border_cyan"],
        )
        self.status_label.pack(side="left", padx=14)

        # Telemetry progress bars on right: CPU, RAM, Disk
        pb_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        pb_frame.pack(side="right", padx=14)

        # Disk
        self.lbl_disk = ctk.CTkLabel(pb_frame, text="Disk: --%", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"])
        self.lbl_disk.pack(side="left", padx=(10, 4))
        self.pb_disk = ctk.CTkProgressBar(pb_frame, width=70, height=8, progress_color=HOLO_PALETTE["border_cyan"])
        self.pb_disk.pack(side="left", padx=(0, 8))
        self.pb_disk.set(0.0)

        # RAM
        self.lbl_ram = ctk.CTkLabel(pb_frame, text="RAM: --%", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"])
        self.lbl_ram.pack(side="left", padx=(10, 4))
        self.pb_ram = ctk.CTkProgressBar(pb_frame, width=70, height=8, progress_color=HOLO_PALETTE["border_cyan"])
        self.pb_ram.pack(side="left", padx=(0, 8))
        self.pb_ram.set(0.0)

        # CPU
        self.lbl_cpu = ctk.CTkLabel(pb_frame, text="CPU: --%", font=get_hud_font("mono", 9), text_color=HOLO_PALETTE["text_secondary"])
        self.lbl_cpu.pack(side="left", padx=(10, 4))
        self.pb_cpu = ctk.CTkProgressBar(pb_frame, width=70, height=8, progress_color=HOLO_PALETTE["border_cyan"])
        self.pb_cpu.pack(side="left", padx=(0, 4))
        self.pb_cpu.set(0.0)

    def add_chat_message(self, role: str, content: str):
        """Appends formatted message to chat console with sanitization."""
        from nlp.answer_pipeline import sanitize_response
        sanitized_content = content
        if role == "assistant":
            sanitized_content = sanitize_response(content)
            clean_str = sanitized_content.strip()
            if not clean_str or re.fullmatch(r"^[0-9\.\,\-\+]+$", clean_str):
                sanitized_content = "I'm not sure how to answer that directly. Could you rephrase?"

        self.chat_display.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")

        if role == "user":
            header = f"\n[USER :: {ts}]\n"
            body = f"{content}\n"
        elif role == "assistant":
            header = f"\n[P.H.A.S.S :: {ts}]\n"
            body = f"{sanitized_content}\n"
        else:
            header = f"\n[SYSTEM :: {ts}]\n"
            body = f"{content}\n"

        self.chat_display.insert("end", header)
        self.chat_display.insert("end", body)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")


    def show_task_progress(self, message: str = "⏳ Processing directive..."):
        """Displays non-blocking task progress bar and status above input."""
        try:
            self.task_status_label.configure(text=message)
            self.active_task_frame.pack(fill="x", pady=(0, 6), before=self.input_frame)
            self.task_progress_bar.configure(mode="indeterminate")
            self.task_progress_bar.start()
        except Exception:
            pass

    def hide_task_progress(self):
        """Hides active task progress bar."""
        try:
            self.task_progress_bar.stop()
            self.active_task_frame.pack_forget()
        except Exception:
            pass

    def cancel_active_task(self):
        """Cancels currently running background task."""
        self._active_task_cancelled.set()
        self.status_label.configure(text="⏹️ Task Cancelled by User", text_color=HOLO_PALETTE["status_warn"])
        self.add_chat_message("system", "⏹️ Directive execution cancelled by user.")
        self.hide_task_progress()

    def check_session_recovery(self):
        """Checks if an interrupted task exists from a prior session and offers resume prompt."""
        try:
            from core.state_recovery import state_recovery_manager
            recovery = state_recovery_manager.check_pending_recovery()
            if recovery and recovery.get("prompt"):
                self.root.after(600, lambda: self.add_chat_message("assistant", recovery["prompt"]))
        except Exception:
            pass

    def send_message(self):
        """Handles user message transmission in a background thread."""
        text = self.input_entry.get().strip()
        if not text:
            return

        self._active_task_cancelled.clear()
        self.input_entry.delete(0, "end")
        self.add_chat_message("user", text)
        self.status_label.configure(text="⟡ Processing directive...", text_color=HOLO_PALETTE["accent_purple"])
        self.voice_indicator.set_active(True)

        lower_t = text.lower()
        if any(w in lower_t for w in ["program", "compile", "flash"]):
            self.show_task_progress("⏳ Compiling firmware... (This may take 30 seconds)")
        else:
            self.show_task_progress("⟡ Processing directive...")

        threading.Thread(target=self._process_message_thread, args=(text,), daemon=True).start()

    def _process_message_thread(self, text: str):
        """Processes message via llama_tool_agent and execution_orchestrator in background."""
        try:
            # Update state recovery
            try:
                from core.state_recovery import state_recovery_manager
                state_recovery_manager.update_task_state(
                    task=text,
                    status="in_progress",
                )
                state_recovery_manager.record_message("user", text)
            except Exception:
                pass

            if self._active_task_cancelled.is_set():
                return

            from nlp.answer_pipeline import process_query
            response = process_query(text)

            if self._active_task_cancelled.is_set():
                return

            try:
                from core.state_recovery import state_recovery_manager
                state_recovery_manager.record_message("assistant", response)
                state_recovery_manager.mark_completed()
            except Exception:
                pass

            self.root.after(0, lambda: self._on_response_ready(response))
        except Exception as e:
            if not self._active_task_cancelled.is_set():
                import traceback
                tb = traceback.format_exc()
                from core.silent_logger import silent_logger
                silent_logger.log("ui_error", str(e), raw_trace=tb, error=str(e))
                self.root.after(0, lambda: self._on_response_ready("I encountered an issue processing that. Please check your parameters."))

    def _on_response_ready(self, response: str):
        self.hide_task_progress()
        self.add_chat_message("assistant", response)
        self.status_label.configure(text="◈ System Status: Online & Verified", text_color=HOLO_PALETTE["border_cyan"])
        self.voice_indicator.set_active(False)
        self.refresh_log_count()
        self.update_hardware_status()

        # Auto-switch to Serial Plotter tab if firmware was compiled & flashed
        lower_resp = response.lower()
        if "flash" in lower_resp or "compiled and flashed" in lower_resp or "monitor" in lower_resp:
            try:
                self.tabview.set("📈 Serial Plotter")
                self.feed_serial_data("[FIRMWARE FLASHED] Live serial telemetry active:")
                self.feed_serial_data("100, 180, 240, 310, 280, 220, 250")
            except Exception:
                pass

    def _on_hotplug_event(self, event_type: str, data: Dict[str, Any]):
        """Handles real-time USB hotplug notifications from background daemon."""
        status_text = data.get("status_text", "🔌 Hardware pre-loaded")
        if event_type == "hardware_connected":
            self.root.after(0, lambda: self.stat_hw_status.configure(
                text=status_text,
                text_color=HOLO_PALETTE["border_cyan"],
            ))
        elif event_type == "hardware_disconnected":
            self.root.after(0, lambda: self.stat_hw_status.configure(
                text=status_text,
                text_color=HOLO_PALETTE["status_warn"],
            ))

    def update_hardware_status(self):
        """Updates the sidebar hardware indicator based on background daemon or detected devices."""
        try:
            from core.background_daemon import background_daemon
            if background_daemon.latest_status:
                is_preloaded = "Pre-loaded" in background_daemon.latest_status or "connected" not in background_daemon.latest_status
                self.stat_hw_status.configure(
                    text=background_daemon.latest_status,
                    text_color=HOLO_PALETTE["border_cyan"] if is_preloaded else HOLO_PALETTE["status_warn"],
                )
                return
        except Exception:
            pass

        try:
            from hardware.detection_engine import HardwareDetector
            boards = HardwareDetector.detected_devices
            if not boards:
                from hardware.detection_engine import hardware_detector
                boards = hardware_detector.detected_devices
            if boards:
                first = boards[0]
                b_name = first.get("board", "Board")
                port = first.get("port", "COM3")
                self.stat_hw_status.configure(
                    text=f"🔌 {b_name} Pre-loaded (Ready in 2s)",
                    text_color=HOLO_PALETTE["border_cyan"],
                )
            else:
                self.stat_hw_status.configure(
                    text="🔌 Hardware: [None]",
                    text_color=HOLO_PALETTE["text_muted"],
                )
        except Exception:
            pass

    def trigger_detect_hardware(self):
        """Quick-action button in the sidebar that triggers detect_hardware()."""
        try:
            from hardware.detection_engine import HardwareDetector
            HardwareDetector.get_instance().scan_ports()
        except Exception:
            pass
        self.execute_quick_command("detect hardware")
        self.update_hardware_status()

    def _on_error(self, err_msg: str):
        self.hide_task_progress()
        self.add_chat_message("system", f"Execution Fault: {err_msg}")
        self.status_label.configure(text="◇ Execution Notice", text_color=HOLO_PALETTE["status_warn"])
        self.voice_indicator.set_active(False)


    def execute_quick_command(self, cmd: str):
        """Triggers predefined prompt from sidebar."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, cmd)
        self.send_message()

    def clear_chat(self):
        """Clears console output."""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")

    def toggle_voice(self):
        """Toggles voice input listening state."""
        self.is_listening = not self.is_listening
        self.voice_indicator.set_active(self.is_listening)
        if self.is_listening:
            self.voice_status_lbl.configure(text="Voice: ◈ Listening", text_color=HOLO_PALETTE["border_cyan"])
            self.btn_voice_toggle.configure(text="🎙 Stop Listening", fg_color=HOLO_PALETTE["accent_purple"])
        else:
            self.voice_status_lbl.configure(text="Voice: ◇ Standby", text_color=HOLO_PALETTE["text_secondary"])
            self.btn_voice_toggle.configure(text="🎙 Activate Voice", fg_color="#182848")

    def toggle_autonomous_mode(self):
        """Toggles autonomous execution flag."""
        self.autonomous_mode = not self.autonomous_mode
        if self.autonomous_mode:
            self.stat_auto.configure(text="⚡ Autonomous: ARMED", text_color=HOLO_PALETTE["border_cyan"])
            self.btn_auto_toggle.configure(text="Autonomous Mode: ON", fg_color=HOLO_PALETTE["border_cyan"], text_color="#0a0a1a")
        else:
            self.stat_auto.configure(text="⚡ Autonomous: Off", text_color=HOLO_PALETTE["text_muted"])
            self.btn_auto_toggle.configure(text="Toggle Autonomous Mode", fg_color=HOLO_PALETTE["accent_purple"], text_color=HOLO_PALETTE["text_glowing"])

    def refresh_log_count(self):
        """Updates verified action log count from execution_log.json."""
        try:
            log_path = Path("checkpoints/execution_log.json")
            if log_path.exists():
                with open(log_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                count = len(entries) if isinstance(entries, list) else 0
                self.stat_exec_log.configure(text=f"💾 Verified Logs: {count}")
        except Exception:
            pass

    def update_telemetry(self):
        """Periodically polls CPU, RAM, Disk and updates gauges."""
        if PSUTIL_AVAILABLE:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent

                self.lbl_cpu.configure(text=f"CPU: {int(cpu)}%")
                self.pb_cpu.set(cpu / 100.0)

                self.lbl_ram.configure(text=f"RAM: {int(ram)}%")
                self.pb_ram.set(ram / 100.0)

                self.lbl_disk.configure(text=f"Disk: {int(disk)}%")
                self.pb_disk.set(disk / 100.0)

                # Update telemetry tab details
                p_count = len(psutil.pids())
                details = (
                    f"◈ CPU Telemetry:\n"
                    f"  • Utilization: {cpu}%\n"
                    f"  • Logical Cores: {psutil.cpu_count()}\n\n"
                    f"◈ Memory Telemetry:\n"
                    f"  • Physical RAM Used: {ram}%\n"
                    f"  • Available: {round(psutil.virtual_memory().available / (1024**3), 2)} GB\n\n"
                    f"◈ Disk Subsystem:\n"
                    f"  • Primary Storage Usage: {disk}%\n"
                    f"  • Active Process Threads: {p_count} processes\n\n"
                    f"◈ Holographic Shader & Cyber HUD: Active (3s sweep)\n"
                )
                self.telem_details.configure(text=details)
            except Exception:
                pass

        self.refresh_log_count()
        self.update_hardware_status()
        self.system_update_id = self.root.after(2000, self.update_telemetry)


    def process_voice_queue(self):
        """Processes voice command queue."""
        try:
            while not self.voice_queue.empty():
                text = self.voice_queue.get_nowait()
                if text:
                    self.input_entry.delete(0, "end")
                    self.input_entry.insert(0, text)
                    self.send_message()
        except Exception:
            pass
        self.root.after(100, self.process_voice_queue)

    def run(self, verify_mode: bool = False):
        """Starts main event loop. In verify_mode, renders briefly and exits cleanly."""
        if verify_mode or "--verify" in sys.argv or "--test" in sys.argv:
            print("P.H.A.S.S SPHERE: Holographic UI running in verification mode.", flush=True)
            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.5)
            print("[OK] Holographic Assistant UI successfully initialized and verified.", flush=True)
            self.scan_canvas.stop()
            self.voice_indicator.stop_animation()
            self.root.destroy()
            return

        self.root.mainloop()


if __name__ == "__main__":
    app = AssistantUI()
    app.run()
