"""
Proactive System Event Monitor for P.H.A.S.S.
Continuously runs as a background monitor scanning for system events:
- USB / Removable drive insertions & serial COM port changes
- High CPU spikes / thermal-load surges
- File drops and external notification triggers
Asynchronously injects alerts into the conversational flow:
"[P.H.A.S.S Interrupts] Sir, I noticed..."
"""

from __future__ import annotations
import os
import sys
import time
import threading
import logging
from typing import Callable, Dict, List, Optional, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger("phass.core.proactive_monitor")


class ProactiveMonitor:
    """
    Background daemon monitoring system state and generating proactive interruptions.
    """
    _instance: Optional[ProactiveMonitor] = None

    def __init__(self, poll_interval: float = 2.0, cpu_threshold: float = 80.0):
        self.poll_interval = poll_interval
        self.cpu_threshold = cpu_threshold
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._listeners: List[Callable[[str], None]] = []

        # Baseline system state tracking
        self._known_partitions: set = self._get_current_partitions()
        self._known_ports: set = self._get_current_ports()
        self._last_cpu_alert: float = 0.0
        self._alert_cooldown: float = 15.0
        self._event_cooldowns: Dict[str, float] = {}
        self.cooldown_duration: float = 300.0  # 5-minute cooldown to stop alert spam

    @classmethod
    def get_instance(cls) -> ProactiveMonitor:
        if cls._instance is None:
            cls._instance = ProactiveMonitor()
        return cls._instance

    def add_listener(self, callback: Callable[[str], None]):
        """Register a callback for asynchronous interruptions."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def trigger_event(
        self,
        event_type: str,
        details: str,
        action: Optional[Dict[str, Any]] = None,
        event_signature: Optional[str] = None,
    ) -> str:
        """
        Explicitly triggers an interruption event with 5-minute cooldown and pending action support.
        Returns the formatted interruption text, or empty string if on cooldown.
        """
        now = time.time()
        sig = event_signature or f"{event_type.lower()}_{details[:30]}"

        # 5-minute cooldown before the same event_signature can trigger another interrupt
        if sig in self._event_cooldowns and (now - self._event_cooldowns[sig]) < self.cooldown_duration:
            logger.debug(f"Event signature '{sig}' throttled by 5-minute cooldown.")
            return ""

        # Record timestamp
        self._event_cooldowns[sig] = now

        clean_details = details.strip()
        message = f"[Orvix Interrupts] Sir, I noticed {clean_details}"

        # If a question is asked or an action is provided, register pending action in conversation buffer
        is_question = "?" in details or "would you like" in details.lower() or action is not None
        if is_question:
            try:
                from core.conversation_buffer import conversation_buffer
                pending_act = action or {"action": "inspect_processes", "args": {"event_type": event_type}}
                conversation_buffer.set_pending_action(pending_act)
            except Exception as e:
                logger.debug(f"Pending action register error: {e}")

        # Inject into conversation buffer if available
        try:
            from core.conversation_buffer import conversation_buffer
            conversation_buffer.inject_interruption(message)
        except Exception:
            pass

        # Notify active callbacks
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(message)
            except Exception as e:
                logger.debug(f"Interruption callback error: {e}")

        return message

    def alert_autonomic_fix(self, module_name: str) -> str:
        """
        Emits proactive interrupt when an autonomous self-repair fix is generated:
        'Sir, I detected an error in my own [module] module. I have generated a fix and am testing it in the sandbox.'
        """
        clean_name = str(module_name).replace("\\", "/").split("/")[-1]
        message = f"[Orvix Interrupts] Sir, I detected an error in my own {clean_name} module. I have generated a fix and am testing it in the sandbox."

        # Inject into conversation buffer if available
        try:
            from core.conversation_buffer import conversation_buffer
            conversation_buffer.inject_interruption(message)
        except Exception:
            pass

        # Notify active callbacks
        with self._lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(message)
            except Exception as e:
                logger.debug(f"Autonomic fix alert callback error: {e}")

        logger.info(f"Proactive alert dispatched: {message}")
        return message

    def _get_current_partitions(self) -> set:
        if not PSUTIL_AVAILABLE:
            return set()
        try:
            parts = psutil.disk_partitions(all=False)
            return {p.device for p in parts}
        except Exception:
            return set()

    def _get_current_ports(self) -> set:
        try:
            import serial.tools.list_ports as list_ports
            return {p.device for p in list_ports.comports()}
        except Exception:
            return set()

    def _check_system_events(self):
        """Polls hardware partitions, COM ports, and CPU utilization."""
        if not PSUTIL_AVAILABLE:
            return

        now = time.time()

        # 1. Check for USB / Drive additions
        curr_parts = self._get_current_partitions()
        new_drives = curr_parts - self._known_partitions
        if new_drives:
            drive_names = ", ".join(sorted(new_drives))
            self.trigger_event("USB_INSERTION", f"a new storage volume ({drive_names}) was plugged in.")
            self._known_partitions = curr_parts
        elif curr_parts != self._known_partitions:
            self._known_partitions = curr_parts

        # 2. Check for Serial COM Port plug-in
        curr_ports = self._get_current_ports()
        new_ports = curr_ports - self._known_ports
        if new_ports:
            port_names = ", ".join(sorted(new_ports))
            self.trigger_event("PORT_INSERTION", f"a new microcontroller or hardware device connected on {port_names}.")
            self._known_ports = curr_ports
        elif curr_ports != self._known_ports:
            self._known_ports = curr_ports

        # 3. Check for CPU Spikes
        try:
            cpu_load = psutil.cpu_percent(interval=None)
            if cpu_load >= self.cpu_threshold:
                sig = "cpu_spike_99" if cpu_load >= 90 else f"cpu_spike_{int(cpu_load)}"
                action = {"action": "inspect_processes", "args": {"cpu_percent": cpu_load}}
                self.trigger_event(
                    "CPU_SPIKE",
                    f"a sudden CPU spike reaching {cpu_load:.1f}%. Would you like me to inspect running processes?",
                    action=action,
                    event_signature=sig,
                )
        except Exception:
            pass

    def _monitor_loop(self):
        while self._running:
            try:
                self._check_system_events()
            except Exception as e:
                logger.debug(f"Proactive monitor cycle notice: {e}")
            time.sleep(self.poll_interval)

    def start(self):
        """Starts the background monitor thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._known_partitions = self._get_current_partitions()
                self._known_ports = self._get_current_ports()
                self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="ProactiveMonitorThread")
                self._thread.start()
                logger.info("Proactive monitor daemon started.")

    def stop(self):
        """Stops the background monitor thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running


# Global singleton instance
proactive_monitor = ProactiveMonitor.get_instance()
