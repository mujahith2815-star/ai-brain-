"""
Headless Background Daemon Service for Orvix Sphere.
Runs background schedulers, watchers, monitors, and optional web server silently with structured rotating logging.
"""

import os
import sys
import time
import signal
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import argparse

logger = logging.getLogger("orvix.daemon")
RUNNING = True


def handle_signal(signum, frame):
    global RUNNING
    logger.info(f"Received termination signal ({signum}). Initiating graceful shutdown...")
    RUNNING = False


def setup_daemon_logging(log_path: str = None):
    """Setup rotating log handler for daemon service."""
    if not log_path:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "daemon.log"
    else:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Reconfigure logger handlers
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] (%(name)s) %(message)s")

    # Rotating file handler (5MB, 3 backups)
    rf_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    rf_handler.setFormatter(formatter)
    logger.addHandler(rf_handler)

    # Console stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info(f"Logging initialized -> {log_file}")
    return log_file


def run_daemon(log_file: str = None, enable_web: bool = False):
    global RUNNING
    RUNNING = True

    setup_daemon_logging(log_file)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("=== Orvix Sphere Headless Daemon Initialized ===")

    sched = None
    fsw = None
    cw = None
    mcp = None

    # 1. Initialize TaskScheduler & Bootstrap triggers
    try:
        from proactive.scheduler import TaskScheduler
        sched = TaskScheduler()
        sched.bootstrap_from_triggers()
        logger.info(f"[+] Task Scheduler active ({len(sched.list_tasks())} tasks scheduled).")
    except Exception as e:
        logger.warning(f"[-] Task Scheduler notice: {e}")

    # 2. Initialize Watchers
    try:
        from proactive.watchers import FileSystemWatcher, ConditionWatcher
        fsw = FileSystemWatcher(watch_paths=["knowledge/inbox"])
        fsw.start()
        cw = ConditionWatcher(poll_interval=30.0)
        cw.start()
        logger.info("[+] FileSystemWatcher and ConditionWatcher armed.")
    except Exception as e:
        logger.warning(f"[-] Watchers notice: {e}")

    # 3. Initialize MCP
    try:
        from mcp.mcp_manager import MCPManager
        mcp = MCPManager()
        mcp.start_all()
        logger.info("[+] MCP Manager initialized.")
    except Exception as e:
        logger.warning(f"[-] MCP notice: {e}")

    # 4. Optional Web Server
    if enable_web:
        try:
            import threading
            import uvicorn
            from web.app import app

            def start_web():
                uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

            t = threading.Thread(target=start_web, daemon=True)
            t.start()
            logger.info("[+] Web Dashboard server listening on http://127.0.0.1:8000")
        except Exception as e:
            logger.warning(f"[-] Web server notice: {e}")

    logger.info("[✓] Background Sentinels active. Standing by...")

    try:
        while RUNNING:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main loop.")

    logger.info("Flushing subsystems and shutting down...")

    # Teardown Watchers
    if fsw:
        try:
            fsw.stop()
        except Exception:
            pass
    if cw:
        try:
            cw.stop()
        except Exception:
            pass

    # Teardown Scheduler
    if sched:
        try:
            sched.stop()
        except Exception:
            pass

    # Teardown MCP
    if mcp:
        try:
            mcp.stop_all()
        except Exception:
            pass

    # Flush database / memory
    try:
        from knowledge.sqlite_store import SQLiteStore
        store = SQLiteStore()
        store.conn.commit()
    except Exception:
        pass

    logger.info("=== Orvix Sphere Daemon Shutdown Complete ===")


def main():
    parser = argparse.ArgumentParser(description="Orvix Sphere Background Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode")
    parser.add_argument("--log", type=str, default=None, help="Custom log file path")
    parser.add_argument("--web", action="store_true", help="Start web dashboard along with daemon")
    args, _ = parser.parse_known_args()

    run_daemon(log_file=args.log, enable_web=args.web)


if __name__ == "__main__":
    main()
