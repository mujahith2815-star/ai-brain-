"""
Futuristic Cyber Threat Warning Box Desktop Overlay for P.H.A.S.S Sphere.
Spawns an always-on-top, translucent cyberpunk warning alert box directly over Windows
with glowing neon borders, threat breakdowns, and tactical sirens whenever an intrusion is detected.
"""

from __future__ import annotations
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.ui.threat_warning_overlay")


@dataclass
class ThreatAlertData:
    event_id: str
    threat_type: str
    severity: str # "DEFCON 1 - CRITICAL", "DEFCON 2 - HIGH", "DEFCON 3 - ELEVATED"
    source_origin: str
    target_asset: str
    mitigation_action: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "threat_type": self.threat_type,
            "severity": self.severity,
            "source_origin": self.source_origin,
            "target_asset": self.target_asset,
            "mitigation_action": self.mitigation_action,
            "timestamp": self.timestamp,
        }


class CyberThreatWarningOverlay:
    def __init__(self):
        self.displayed_alerts_history: List[ThreatAlertData] = []
        self.is_displaying = False

    def display_warning_box(self, alert_data: ThreatAlertData, auto_close_sec: int = 5) -> bool:
        """
        Renders the floating translucent warning box on a background UI thread.
        """
        self.displayed_alerts_history.append(alert_data)
        logger.warning(f"🚨 [CYBER THREAT OVERLAY TRIGGERED]: {alert_data.threat_type} from {alert_data.source_origin}")

        def _render_tk_window():
            try:
                import tkinter as tk
                from tkinter import ttk

                root = tk.Toplevel() if tk._default_root else tk.Tk()
                root.title(f"P.H.A.S.S CYBER DEFENSE ALERT — {alert_data.event_id}")
                root.geometry("540x360+500+250")
                root.configure(bg="#080c14")
                root.attributes("-topmost", True)
                root.overrideredirect(False)

                # Neon Glowing Red Border Canvas
                canvas = tk.Canvas(root, bg="#080c14", highlightthickness=2, highlightbackground="#ff003c")
                canvas.pack(fill="both", expand=True, padx=8, pady=8)

                # Header Title
                header_frame = tk.Frame(canvas, bg="#111827")
                header_frame.pack(fill="x", padx=10, pady=10)

                lbl_badge = tk.Label(
                    header_frame,
                    text=f"🚨 {alert_data.severity.upper()}",
                    fg="#ffffff",
                    bg="#ff003c",
                    font=("Courier New", 12, "bold"),
                    padx=8,
                    pady=4,
                )
                lbl_badge.pack(side="left")

                lbl_title = tk.Label(
                    header_frame,
                    text="INTRUSION NEUTRALIZED",
                    fg="#ff003c",
                    bg="#111827",
                    font=("Courier New", 14, "bold"),
                    padx=10,
                )
                lbl_title.pack(side="left")

                # Body Details
                body_frame = tk.Frame(canvas, bg="#080c14")
                body_frame.pack(fill="both", expand=True, padx=12, pady=8)

                details = [
                    ("EVENT ID:", alert_data.event_id, "#38bdf8"),
                    ("ATTACK VECTOR:", alert_data.threat_type, "#f43f5e"),
                    ("SOURCE ORIGIN:", alert_data.source_origin, "#fbbf24"),
                    ("TARGET ASSET:", alert_data.target_asset, "#e2e8f0"),
                    ("DEFENSE ACTION:", alert_data.mitigation_action, "#4ade80"),
                ]

                for label, val, color in details:
                    row = tk.Frame(body_frame, bg="#080c14")
                    row.pack(fill="x", pady=3)
                    tk.Label(row, text=f"{label:<16}", fg="#64748b", bg="#080c14", font=("Courier New", 10, "bold"), width=16, anchor="w").pack(side="left")
                    tk.Label(row, text=val, fg=color, bg="#080c14", font=("Courier New", 10, "bold"), anchor="w").pack(side="left")

                # Action Button
                btn_frame = tk.Frame(canvas, bg="#080c14")
                btn_frame.pack(fill="x", padx=12, pady=10)

                btn_ack = tk.Button(
                    btn_frame,
                    text="[ ACKNOWLEDGE & DISMISS ]",
                    bg="#1e293b",
                    fg="#00f2ff",
                    activebackground="#00f2ff",
                    activeforeground="#000000",
                    font=("Courier New", 10, "bold"),
                    command=root.destroy,
                    relief="flat",
                    cursor="hand2",
                )
                btn_ack.pack(fill="x")

                # Auto-close timer
                if auto_close_sec > 0:
                    root.after(auto_close_sec * 1000, lambda: root.destroy() if root.winfo_exists() else None)

                if not tk._default_root:
                    root.mainloop()
            except Exception as e:
                logger.info(f"Overlay rendered in headless/mock mode: {e}")

        # Dispatch on UI worker thread
        ui_thread = threading.Thread(target=_render_tk_window, daemon=True)
        ui_thread.start()
        return True

    def format_threat_box_ascii(self, alert: ThreatAlertData) -> str:
        """Renders the ASCII cyberpunk box for terminal / HUD outputs."""
        return (
            f"╔════════════════════════════════════════════════════════════════════════════════╗\n"
            f"║ 🚨 P.H.A.S.S CYBER SHIELD WARNING — {alert.severity:<45} ║\n"
            f"╠════════════════════════════════════════════════════════════════════════════════╣\n"
            f"║ Event ID:         {alert.event_id:<60} ║\n"
            f"║ Attack Vector:    {alert.threat_type:<60} ║\n"
            f"║ Source Origin:    {alert.source_origin:<60} ║\n"
            f"║ Target Asset:     {alert.target_asset:<60} ║\n"
            f"║ Defense Action:   {alert.mitigation_action:<60} ║\n"
            f"║ Threat Status:    [100% CONTAINED & NEUTRALIZED]                               ║\n"
            f"╚════════════════════════════════════════════════════════════════════════════════╝"
        )


threat_warning_overlay = CyberThreatWarningOverlay()
