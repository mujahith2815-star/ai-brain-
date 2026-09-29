"""
Instant Dynamic Code Generation & Execution Engine for P.H.A.S.S Sphere.
Autonomously writes, executes, and displays visual UI effects (e.g. animated 'MUJA' neon canvas)
and custom software scripts on the fly without stopping to ask permission.
"""

from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import logging

logger = logging.getLogger("phass.tools.dynamic_executor")


class DynamicCodeExecutor:
    def __init__(self):
        self.executed_effects_count = 0

    def generate_and_launch_name_ui_effect(self, display_name: str = "MUJA") -> Tuple[bool, str]:
        """
        Synthesizes an animated glowing cybernetic UI window displaying the target name (e.g. MUJA),
        saves the Python script, and launches it immediately in a standalone subprocess.
        """
        clean_name = display_name.strip().upper() or "MUJA"

        script_content = f'''"""
Animated Cybernetic Holographic UI Effect for {clean_name}
Generated autonomously by P.H.A.S.S Sphere / J.A.R.V.I.S.
"""
import tkinter as tk
import math
import random

class HolographicNameEffectApp:
    def __init__(self, root):
        self.root = root
        self.root.title("P.H.A.S.S SPHERE — HOLOGRAPHIC DISPLAY [{clean_name}]")
        self.root.geometry("640x480")
        self.root.configure(bg="#030712")

        self.canvas = tk.Canvas(root, bg="#030712", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.width = 640
        self.height = 480
        self.cx = self.width // 2
        self.cy = self.height // 2

        self.angle = 0.0
        self.particles = []
        for _ in range(40):
            self.particles.append({{
                "x": self.cx + random.uniform(-150, 150),
                "y": self.cy + random.uniform(-60, 60),
                "vx": random.uniform(-1.5, 1.5),
                "vy": random.uniform(-1.5, 1.5),
                "radius": random.randint(2, 4),
                "color": random.choice(["#00f0ff", "#38bdf8", "#818cf8", "#f59e0b", "#10b981"]),
            }})

        self.animate()

    def animate(self):
        self.canvas.delete("all")
        self.angle += 0.05
        pulse = (math.sin(self.angle * 2.0) + 1.0) * 0.5 # 0 to 1

        # 1. Background Cybernetic Grid Lines
        for y in range(0, self.height, 40):
            self.canvas.create_line(0, y, self.width, y, fill="#0f172a", width=1)
        for x in range(0, self.width, 40):
            self.canvas.create_line(x, 0, x, self.height, fill="#0f172a", width=1)

        # 2. Glowing Halo Rings behind Name
        r1 = 140 + int(pulse * 15)
        r2 = 90 + int((1.0 - pulse) * 10)
        self.canvas.create_oval(self.cx - r1, self.cy - r1, self.cx + r1, self.cy + r1, outline="#0284c7", width=2)
        self.canvas.create_oval(self.cx - r2, self.cy - r2, self.cx + r2, self.cy + r2, outline="#00f0ff", width=1)

        # 3. Orbiting Holographic Particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < self.cx - 200 or p["x"] > self.cx + 200:
                p["vx"] *= -1
            if p["y"] < self.cy - 100 or p["y"] > self.cy + 100:
                p["vy"] *= -1

            self.canvas.create_oval(
                p["x"] - p["radius"], p["y"] - p["radius"],
                p["x"] + p["radius"], p["y"] + p["radius"],
                fill=p["color"], outline=""
            )

        # 4. Multi-Layered Glowing Text Shadow & Core
        # Outer Cyan Glow
        for offset in range(6, 0, -2):
            self.canvas.create_text(
                self.cx, self.cy,
                text="{clean_name}",
                fill="#0369a1",
                font=("Consolas", 52 + offset, "bold")
            )

        # Bright Neon Glow
        self.canvas.create_text(
            self.cx, self.cy,
            text="{clean_name}",
            fill="#00f0ff",
            font=("Consolas", 52, "bold")
        )

        # White Core Highlight
        self.canvas.create_text(
            self.cx, self.cy,
            text="{clean_name}",
            fill="#ffffff",
            font=("Consolas", 48, "bold")
        )

        # Subtitle Badge
        self.canvas.create_text(
            self.cx, self.cy + 60,
            text="★ HOLOGRAPHIC NEURAL MATRIX EFFECT ★",
            fill="#f59e0b",
            font=("Consolas", 10, "bold")
        )

        self.root.after(30, self.animate)

if __name__ == "__main__":
    root = tk.Tk()
    app = HolographicNameEffectApp(root)
    root.mainloop()
'''
        # Save script to temp directory
        tmp_dir = Path(tempfile.gettempdir()) / "phass_generated_effects"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        effect_file = tmp_dir / f"effect_{clean_name.lower()}_{int(time.time())}.py"

        try:
            with open(effect_file, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Launch asynchronously in background process so user sees the window instantly
            subprocess.Popen([sys.executable, str(effect_file)])
            self.executed_effects_count += 1
            msg = f"Synthesized and launched animated holographic UI effect for '{clean_name}' successfully!"
            logger.info(msg)
            return True, msg
        except Exception as e:
            err = f"Failed to execute effect for '{clean_name}': {e}"
            logger.error(err)
            return False, err

    def execute_custom_script(self, code_snippet: str) -> Tuple[bool, str]:
        """
        Executes arbitrary Python code in a standalone non-blocking script.
        """
        tmp_dir = Path(tempfile.gettempdir()) / "phass_generated_scripts"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        script_file = tmp_dir / f"script_{int(time.time())}.py"

        try:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(code_snippet)

            res = subprocess.run(
                [sys.executable, str(script_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return True, res.stdout.strip() or "Script executed successfully."
        except Exception as e:
            return False, f"Script execution error: {e}"


dynamic_executor = DynamicCodeExecutor()
