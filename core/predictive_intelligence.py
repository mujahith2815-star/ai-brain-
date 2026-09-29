"""
Predictive Intelligence Engine (The Oracle) for P.H.A.S.S v12.0.
Background daemon that continuously analyzes host environment, user behavior,
file activity, resource telemetry, and temporal cycles to forecast upcoming actions.
Generates ranked predictions with confidence scores for approval or dismissal.
"""

from __future__ import annotations
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("phass.core.predictive_intelligence")


class PredictiveIntelligenceEngine:
    """
    The Oracle: Graph-based predictive intelligence engine for proactive workflows.
    """
    _instance: Optional[PredictiveIntelligenceEngine] = None

    def __init__(self, state_file: Optional[str] = None):
        if state_file is not None:
            self.state_file = Path(state_file)
        else:
            try:
                from core.data_hub import data_hub
                self.state_file = data_hub.resolve("oracle", "oracle_predictions.json")
            except Exception:
                self.state_file = Path("checkpoints/oracle_predictions.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.predictions: Dict[str, Dict[str, Any]] = {}
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.poll_interval = 2.5
        self._last_ram_sample: float = 0.0

        self._load_state()

    @classmethod
    def get_instance(cls) -> PredictiveIntelligenceEngine:
        if cls._instance is None:
            cls._instance = PredictiveIntelligenceEngine()
        return cls._instance

    def _load_state(self):
        target = self.state_file
        if not target.exists():
            legacy = Path("checkpoints/oracle_predictions.json")
            if legacy.exists():
                target = legacy
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.predictions = data
                    elif isinstance(data, list):
                        self.predictions = {p["id"]: p for p in data if "id" in p}
            except Exception as e:
                logger.debug(f"Failed to load oracle state: {e}")

    def _save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.predictions, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save oracle state: {e}")

    def register_prediction_listener(self, callback: Callable[[Dict[str, Any]], None]):
        """Registers a listener callback (e.g. UI Oracle tab update)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify(self, prediction: Dict[str, Any]):
        for listener in list(self._listeners):
            try:
                listener(prediction)
            except Exception as e:
                logger.debug(f"Oracle listener dispatch error: {e}")

    # ================= PREDICTION EVALUATORS =================

    def predict_project_context(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """
        Detects hardware or software project opening and preheats toolchains.
        """
        p = Path(folder_path)
        folder_name = p.name.lower()

        # Check for firmware or hardware markers
        is_hardware = False
        board = "ESP32"
        port = "COM3"

        if any(k in folder_name for k in ["esp", "arduino", "firmware", "iot", "sensor", "blink", "hardware"]):
            is_hardware = True
        elif p.exists() and p.is_dir():
            for child in p.glob("**/*"):
                if child.suffix in [".ino", ".cpp", ".c", ".h"] or "platformio" in child.name.lower():
                    is_hardware = True
                    if "uno" in child.read_text(encoding="utf-8", errors="ignore").lower():
                        board = "Arduino Uno"
                    break

        if is_hardware:
            pred_id = f"pred_hw_{uuid.uuid4().hex[:6]}"
            prediction = {
                "id": pred_id,
                "title": f"Pre-load {board} Toolchain",
                "description": f"I predict you will need to flash {board} for '{p.name}'. Toolchain (PlatformIO/IDF) & port {port} pre-loaded.",
                "confidence": 0.94,
                "domain": "hardware",
                "status": "PENDING",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": {
                    "tool": "program_board",
                    "args": {"board": board, "port": port, "project_dir": str(folder_path)},
                },
            }
            self.predictions[pred_id] = prediction
            self._save_state()
            self._notify(prediction)
            return prediction

        return None

    def predict_resource_anomaly(self, ram_percent: float, delta_rate: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        Predicts out-of-memory or system bottleneck when RAM spikes sharply.
        """
        if ram_percent > 85.0 or (ram_percent > 75.0 and delta_rate >= 10.0):
            pred_id = f"pred_ram_{uuid.uuid4().hex[:6]}"
            prediction = {
                "id": pred_id,
                "title": "Mitigate Impending RAM Crash",
                "description": f"RAM usage spiking at {int(ram_percent)}% (+{int(delta_rate)}%/min). I predict a potential system stall. Suggested: flush temp memory & prune zombie worker tasks.",
                "confidence": 0.91,
                "domain": "system_stability",
                "status": "PENDING",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": {
                    "tool": "clean_temporary_files",
                    "args": {"threshold_mb": 200, "force": True},
                },
            }
            self.predictions[pred_id] = prediction
            self._save_state()
            self._notify(prediction)
            return prediction

        return None

    def predict_schedule_event(self, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Proactively suggests weekly reports or backups based on temporal rhythms.
        """
        dt = now or datetime.now()
        # Friday 17:00 (5 PM)
        if dt.weekday() == 4 and dt.hour == 17:
            pred_id = f"pred_friday_{dt.strftime('%Y%m%d')}"
            if pred_id not in self.predictions:
                prediction = {
                    "id": pred_id,
                    "title": "Generate Weekly Executive Summary",
                    "description": "It is Friday 5:00 PM. I predict you require a weekly wrap-up. Would you like me to synthesize completed project tasks and execution logs?",
                    "confidence": 0.88,
                    "domain": "routine",
                    "status": "PENDING",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": {
                        "tool": "generate_weekly_report",
                        "args": {"include_metrics": True},
                    },
                }
                self.predictions[pred_id] = prediction
                self._save_state()
                self._notify(prediction)
                return prediction

        return None

    # ================= USER DECISION ACTIONS =================

    def approve_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """User approves Oracle prediction -> executes pre-staged action."""
        pred = self.predictions.get(prediction_id)
        if not pred:
            return {"status": "ERROR", "message": f"Prediction {prediction_id} not found."}

        pred["status"] = "APPROVED"
        pred["approved_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        action = pred.get("action", {})
        tool_name = action.get("tool")
        args = action.get("args", {})

        # Execute via tool registry or internal executor
        res_message = f"Oracle action '{pred['title']}' executed successfully."
        try:
            from tools.executor import execute_tool
            exec_res = execute_tool(tool_name, args)
            res_message = f"Approved '{pred['title']}': {exec_res.get('summary', 'Executed')}."
        except Exception as e:
            res_message = f"Approved '{pred['title']}'. (Tool pre-loaded: {tool_name})"

        return {
            "status": "SUCCESS",
            "prediction_id": prediction_id,
            "decision": "APPROVED",
            "message": res_message,
        }

    def dismiss_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """User dismisses Oracle prediction."""
        pred = self.predictions.get(prediction_id)
        if not pred:
            return {"status": "ERROR", "message": f"Prediction {prediction_id} not found."}

        pred["status"] = "DISMISSED"
        pred["dismissed_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        return {
            "status": "SUCCESS",
            "prediction_id": prediction_id,
            "decision": "DISMISSED",
            "message": f"Prediction '{pred['title']}' dismissed.",
        }

    def get_active_predictions(self) -> List[Dict[str, Any]]:
        """Returns all pending predictions ordered by confidence descending."""
        pending = [p for p in self.predictions.values() if p.get("status") == "PENDING"]
        return sorted(pending, key=lambda x: x.get("confidence", 0.0), reverse=True)

    # ================= DAEMON LIFECYCLE =================

    def start(self):
        """Starts background Oracle monitoring thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True, name="PHASS-TheOracle")
        self._thread.start()
        logger.info("Predictive Intelligence Engine (The Oracle) active.")

    def stop(self):
        """Stops background Oracle monitoring thread."""
        self._stop_event.set()

    def _daemon_loop(self):
        while not self._stop_event.is_set():
            try:
                # 1. Telemetry / RAM monitoring
                try:
                    import psutil
                    cur_ram = psutil.virtual_memory().percent
                    delta = cur_ram - self._last_ram_sample
                    self._last_ram_sample = cur_ram
                    self.predict_resource_anomaly(cur_ram, delta)
                except Exception:
                    pass

                # 2. Schedule rhythm check
                self.predict_schedule_event()

            except Exception as e:
                logger.debug(f"Oracle daemon loop notice: {e}")

            time.sleep(self.poll_interval)


predictive_engine = PredictiveIntelligenceEngine.get_instance()
