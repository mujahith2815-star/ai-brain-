"""
File and Condition Watchers for Proactive Autonomous Layer.
Provides file change reactions and edge-triggered system condition alerts.
"""

import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger("orvix.proactive.watchers")


class FileSystemWatcher:
    """
    Monitors designated directories for file creation, modification, or deletion.
    """

    def __init__(
        self,
        watch_paths: Optional[List[str]] = None,
        callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.watch_paths = [Path(p) for p in (watch_paths or [])]
        self.callback = callback
        self._observer = None
        self._running = False
        self._lock = threading.Lock()

    def add_watch(self, path: str, callback: Optional[Callable[[str, str], None]] = None) -> None:
        """Adds a directory to watch list."""
        p = Path(path)
        with self._lock:
            if p not in self.watch_paths:
                self.watch_paths.append(p)
            if callback is not None:
                self.callback = callback

    def start(self) -> bool:
        """Starts watchdog observer thread."""
        with self._lock:
            if self._running:
                return True
            if not WATCHDOG_AVAILABLE:
                logger.warning("Watchdog not installed. FileSystemWatcher in standby mode.")
                self._running = True
                return False

            try:
                self._observer = Observer()

                class _Handler(FileSystemEventHandler):
                    def __init__(self, outer):
                        self.outer = outer

                    def on_created(self, event):
                        if self.outer.callback and not event.is_directory:
                            self.outer.callback("created", event.src_path)

                    def on_modified(self, event):
                        if self.outer.callback and not event.is_directory:
                            self.outer.callback("modified", event.src_path)

                    def on_deleted(self, event):
                        if self.outer.callback and not event.is_directory:
                            self.outer.callback("deleted", event.src_path)

                handler = _Handler(self)
                for wp in self.watch_paths:
                    wp.mkdir(parents=True, exist_ok=True)
                    self._observer.schedule(handler, str(wp), recursive=False)

                self._observer.start()
                self._running = True
                return True
            except Exception as e:
                logger.error(f"Failed to start FileSystemWatcher: {e}")
                self._running = False
                return False

    def stop(self) -> None:
        """Stops watchdog observer."""
        with self._lock:
            if self._observer is not None:
                try:
                    self._observer.stop()
                    self._observer.join(timeout=2.0)
                except Exception:
                    pass
                self._observer = None
            self._running = False

    def simulate_event(self, event_type: str, file_path: str) -> None:
        """Helper for deterministic testing."""
        if self.callback:
            self.callback(event_type, file_path)


class ConditionWatcher:
    """
    Edge-triggered condition monitor. Only fires callback when a condition transitions
    from False to True.
    """

    def __init__(self, poll_interval: float = 30.0):
        self.poll_interval = poll_interval
        self._conditions: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_condition(
        self,
        name: str,
        check_fn: Callable[[], bool],
        callback: Callable[[str], None],
    ) -> None:
        """
        Registers an edge-triggered condition predicate.
        """
        with self._lock:
            self._conditions[name] = {
                "check_fn": check_fn,
                "callback": callback,
                "last_state": False,
            }

    def poll(self) -> None:
        """
        Evaluates all registered conditions once and fires callbacks on False -> True edge.
        """
        with self._lock:
            items = list(self._conditions.items())

        for name, c_data in items:
            try:
                curr_state = bool(c_data["check_fn"]())
            except Exception as e:
                logger.debug(f"Error checking condition {name}: {e}")
                curr_state = False

            prev_state = c_data["last_state"]
            if curr_state and not prev_state:
                # Edge triggered!
                try:
                    c_data["callback"](name)
                except Exception as ex:
                    logger.error(f"Condition callback failed for '{name}': {ex}")

            with self._lock:
                if name in self._conditions:
                    self._conditions[name]["last_state"] = curr_state

    def add_cpu_threshold(self, threshold_percent: float, callback: Callable[[str], None]) -> None:
        """Convenience method to watch for high CPU surges."""
        def _check():
            if not PSUTIL_AVAILABLE:
                return False
            return psutil.cpu_percent(interval=None) > threshold_percent

        self.add_condition(f"cpu_over_{threshold_percent}", _check, callback)

    def add_low_disk_threshold(self, min_free_gb: float, path: str, callback: Callable[[str], None]) -> None:
        """Convenience method to watch for low disk space."""
        def _check():
            if not PSUTIL_AVAILABLE:
                return False
            try:
                free_gb = psutil.disk_usage(path).free / (1024 ** 3)
                return free_gb < min_free_gb
            except Exception:
                return False

        self.add_condition(f"disk_free_under_{min_free_gb}gb", _check, callback)

    def start(self) -> None:
        """Starts condition polling loop in background."""
        with self._lock:
            if self._running:
                return
            self._running = True

            def _loop():
                while self._running:
                    self.poll()
                    time.sleep(self.poll_interval)

            self._thread = threading.Thread(target=_loop, daemon=True, name="ConditionWatcher")
            self._thread.start()

    def stop(self) -> None:
        """Stops condition polling loop."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
