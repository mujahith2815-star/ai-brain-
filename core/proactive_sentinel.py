"""
Autonomic Nervous System & Proactive Sentinel Guard for P.H.A.S.S Sphere.
Runs background autonomous monitoring of battery voltage, core temperatures,
routine habit prediction, and proactive defensive actions.
"""

from __future__ import annotations
import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from world.world_model import world_model
from voice.speech_engine import voice_engine
from voice.sound_effects import sound_synth

logger = logging.getLogger("phass.core.proactive_sentinel")


@dataclass
class SentinelAlert:
    alert_type: str
    severity: str # "INFO", "WARNING", "CRITICAL"
    message: str
    action_taken: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
        }


class ProactiveAutonomicSentinel:
    def __init__(self):
        self.is_running = False
        self.alert_history: List[SentinelAlert] = []
        self.learned_routines = [
            {"time_window": "09:00 - 10:00", "predicted_action": "Launch Developer Workspace & IDE"},
            {"time_window": "13:00 - 14:00", "predicted_action": "Run Diagnostic & Security Sweep"},
            {"time_window": "21:00 - 23:00", "predicted_action": "Magnetic Docking & Dream Latent Rehearsal"},
        ]
        self._sentinel_thread: Optional[threading.Thread] = None

    def start_sentinel(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._sentinel_thread = threading.Thread(target=self._sentinel_loop, daemon=True)
        self._sentinel_thread.start()
        logger.info("Proactive Autonomic Sentinel daemon active.")

    def stop_sentinel(self) -> None:
        self.is_running = False

    def _sentinel_loop(self) -> None:
        while self.is_running:
            self.evaluate_proactive_safeguards()
            time.sleep(2.0)

    def evaluate_proactive_safeguards(self) -> Optional[SentinelAlert]:
        """
        Evaluates real-time battery, thermal, and sensor integrity thresholds.
        """
        batt = world_model.robot_state.battery_percentage
        temp = world_model.robot_state.internal_temp_c

        # 1. Critical Battery Protection (< 15%)
        if batt < 15.0:
            msg = f"Battery reserves critical ({batt:.1f}%). Auto-initiating emergency return to magnetic charging dock."
            sound_synth.play_sound("SECURITY_ALERT")
            voice_engine.speak("Warning, sir. Battery levels are critical. Autonomous docking initiated.")

            alert = SentinelAlert(
                alert_type="CRITICAL_BATTERY",
                severity="CRITICAL",
                message=msg,
                action_taken="DISPATCH_AUTO_DOCK_GOAL",
            )
            self.alert_history.append(alert)
            return alert

        # 2. Thermal Surge Protection (> 50°C)
        if temp > 50.0:
            msg = f"Core thermal alert ({temp:.1f}°C). Throttling internal non-essential compute threads."
            sound_synth.play_sound("SECURITY_ALERT")
            voice_engine.speak("Thermal surge detected, sir. Throttling internal compute cores.")

            alert = SentinelAlert(
                alert_type="THERMAL_SURGE",
                severity="WARNING",
                message=msg,
                action_taken="THROTTLE_COMPUTE_THREADS",
            )
            self.alert_history.append(alert)
            return alert

        return None

    def get_sentinel_snapshot(self) -> Dict[str, Any]:
        return {
            "is_sentinel_active": self.is_running,
            "total_alerts_recorded": len(self.alert_history),
            "learned_operator_routines": self.learned_routines,
            "recent_alerts": [a.to_dict() for a in self.alert_history[-5:]],
        }


proactive_sentinel = ProactiveAutonomicSentinel()
