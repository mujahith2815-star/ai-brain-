"""
Holographic Arc-Reactor & Real-Time Voice Waveform Visualizer for P.H.A.S.S Sphere GUI.
Renders the animated pulsing J.A.R.V.I.S. Arc-Reactor and audio frequency equalizer on Tkinter Canvas.
"""

from __future__ import annotations
import math
import random
import tkinter as tk
from typing import List, Tuple
from voice.speech_engine import voice_engine


class JarvisArcReactorRenderer:
    def __init__(self, canvas: tk.Canvas, width: int = 420, height: int = 320):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.cx = width // 2
        self.cy = height // 2 - 20
        self.angle = 0.0
        self.pulse = 0.0
        self.waveform_bars = [10.0] * 24

    def render_frame(self) -> None:
        self.canvas.delete("all")
        self.angle += 0.04
        self.pulse = (math.sin(self.angle * 2.0) + 1.0) * 0.5 # 0.0 to 1.0

        is_speaking = voice_engine.is_speaking
        core_color = "#00f0ff" if not is_speaking else "#38bdf8"
        gold_color = "#f59e0b"

        # 1. Outer Holographic Ring (Radius 100)
        r_outer = 95
        self.canvas.create_oval(self.cx - r_outer, self.cy - r_outer, self.cx + r_outer, self.cy + r_outer, outline="#082f49", width=2)

        # 2. Rotating Segmented Energy Ticks
        num_segments = 12
        for i in range(num_segments):
            theta = self.angle + (i * 2.0 * math.pi / num_segments)
            x1 = self.cx + (r_outer - 12) * math.cos(theta)
            y1 = self.cy + (r_outer - 12) * math.sin(theta)
            x2 = self.cx + r_outer * math.cos(theta)
            y2 = self.cy + r_outer * math.sin(theta)
            self.canvas.create_line(x1, y1, x2, y2, fill=core_color if i % 2 == 0 else gold_color, width=2)

        # 3. Middle Energy Containment Ring (Radius 65)
        r_mid = 65
        self.canvas.create_oval(self.cx - r_mid, self.cy - r_mid, self.cx + r_mid, self.cy + r_mid, outline="#0284c7", width=3)

        # Inner Tri-Segment Arc Reactor Nodes
        for j in range(3):
            theta = -self.angle * 1.5 + (j * 2.0 * math.pi / 3)
            nx = self.cx + 45 * math.cos(theta)
            ny = self.cy + 45 * math.sin(theta)
            nr = 8 + int(self.pulse * 3)
            self.canvas.create_oval(nx - nr, ny - nr, nx + nr, ny + nr, fill=gold_color, outline="#ffffff")

        # 4. Central Glowing Arc Reactor Core (Radius 24)
        r_core = 22 + int(self.pulse * 4)
        # Glow halo
        self.canvas.create_oval(self.cx - r_core - 4, self.cy - r_core - 4, self.cx + r_core + 4, self.cy + r_core + 4, outline="#38bdf8", width=2)
        self.canvas.create_oval(self.cx - r_core, self.cy - r_core, self.cx + r_core, self.cy + r_core, fill="#ffffff" if is_speaking else core_color, outline="#38bdf8")

        # 5. Audio Waveform Frequency Equalizer at Bottom
        eq_y = self.height - 35
        bar_w = 10
        spacing = 5
        start_x = (self.width - (len(self.waveform_bars) * (bar_w + spacing))) // 2

        for k in range(len(self.waveform_bars)):
            # Modulate bar heights based on speech / pulse
            if is_speaking:
                target_h = random.uniform(8.0, 32.0)
            else:
                target_h = 4.0 + 3.0 * math.sin(self.angle * 3.0 + k * 0.4)

            self.waveform_bars[k] += (target_h - self.waveform_bars[k]) * 0.35
            h = self.waveform_bars[k]
            bx = start_x + k * (bar_w + spacing)

            self.canvas.create_rectangle(bx, eq_y - h, bx + bar_w, eq_y, fill=core_color if k % 3 != 0 else gold_color, outline="")

        # 6. HUD Badges & Labels
        self.canvas.create_text(
            15, 15,
            text="J.A.R.V.I.S. ARC-REACTOR CORE",
            fill="#00f0ff",
            font=("Consolas", 9, "bold"),
            anchor="nw",
        )
        status_str = "VOICE OUTPUT: SPEAKING..." if is_speaking else "VOICE OUTPUT: STANDBY"
        self.canvas.create_text(
            15, 32,
            text=status_str,
            fill=gold_color if is_speaking else "#64748b",
            font=("Consolas", 8, "bold"),
            anchor="nw",
        )
