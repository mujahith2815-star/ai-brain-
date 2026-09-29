"""
Daily Health Check and Alerting Engine for Orvix Sphere (v1.4.4).
Validates SystemDoctor diagnostics, 24-hour error frequency, disk capacity,
MCP server availability, and proactive task scheduling.
Dispatches multi-channel alerts (Windows toast notifications, SMTP email, and audit logs)
if any check fails.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure project's custom logging directory is registered in logging.__path__
_proj_logging_dir = str(BASE_DIR / "logging")
if hasattr(logging, "__path__") and _proj_logging_dir not in logging.__path__:
    logging.__path__.append(_proj_logging_dir)

# Setup logger for health checks
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_LOG_FILE = LOGS_DIR / "health_checks.log"
HEALTH_HISTORY_FILE = LOGS_DIR / "health_history.json"

logger = logging.getLogger("orvix.daily_health_check")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(HEALTH_LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


def check_system_doctor(workspace: Path) -> Dict[str, Any]:
    """Check 1: Runs comprehensive SystemDoctor diagnostics."""
    try:
        from diagnostics.doctor import SystemDoctor
        doctor = SystemDoctor(workspace=workspace)
        report = doctor.run_full_check()
        passed = bool(report.get("healthy", False))
        passed_cnt = report.get("passed_checks", 0)
        total_cnt = report.get("total_checks", 0)
        failing = [f"{c.get('check')} ({c.get('message')})" for c in report.get("checks", []) if not c.get("passed")]
        fail_msg = f" (failed: {', '.join(failing)})" if failing else ""
        return {
            "name": "SystemDoctor Diagnostics",
            "passed": passed,
            "message": f"{passed_cnt}/{total_cnt} subsystem checks passed{fail_msg}",
            "details": report.get("checks", []),
        }
    except Exception as e:
        return {
            "name": "SystemDoctor Diagnostics",
            "passed": False,
            "message": f"Diagnostics error: {e}",
            "details": [],
        }


def check_recent_errors(workspace: Path, hours: int = 24, max_allowed: int = 0) -> Dict[str, Any]:
    """Check 2: Checks error occurrences in the last 24 hours from logs/errors.db."""
    db_path = workspace / "logs" / "errors.db"
    if not db_path.exists():
        return {
            "name": "24h Error Rate",
            "passed": True,
            "message": "0 errors recorded in last 24h (database clean)",
            "error_count": 0,
            "unique_errors": 0,
        }

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(count), 0) FROM errors WHERE last_seen >= ?;",
                (cutoff,),
            )
            row = cursor.fetchone()
            unique_cnt = row[0] if row else 0
            total_occurrences = row[1] if row else 0

        passed = total_occurrences <= max_allowed
        msg = (
            f"0 errors recorded in last {hours}h"
            if total_occurrences == 0
            else f"{total_occurrences} error occurrences ({unique_cnt} unique) in last {hours}h"
        )
        return {
            "name": "24h Error Rate",
            "passed": passed,
            "message": msg,
            "error_count": total_occurrences,
            "unique_errors": unique_cnt,
        }
    except Exception as e:
        return {
            "name": "24h Error Rate",
            "passed": False,
            "message": f"Error database check failed: {e}",
            "error_count": -1,
            "unique_errors": -1,
        }


def check_disk_space(workspace: Path, min_gb: float = 1.0) -> Dict[str, Any]:
    """Check 3: Checks disk capacity on workspace drive and W: drive."""
    try:
        # Check workspace drive (C:)
        usage = shutil.disk_usage(str(workspace))
        free_c_gb = usage.free / (1024 ** 3)
        passed_c = free_c_gb >= min_gb

        # Check W: drive if available
        w_drive = Path("W:\\")
        w_avail = w_drive.exists()
        free_w_gb = None
        passed_w = True

        if w_avail:
            try:
                w_usage = shutil.disk_usage(str(w_drive))
                free_w_gb = w_usage.free / (1024 ** 3)
                passed_w = free_w_gb >= min_gb
            except Exception:
                pass

        overall_passed = passed_c and passed_w

        details_str = f"Workspace disk: {free_c_gb:.2f} GB free (>= {min_gb} GB required)"
        if free_w_gb is not None:
            details_str += f", W: drive: {free_w_gb:.2f} GB free"

        if not overall_passed:
            details_str = f"Low disk space: {details_str}"

        return {
            "name": "Disk Capacity",
            "passed": overall_passed,
            "message": details_str,
            "free_c_gb": round(free_c_gb, 2),
            "free_w_gb": round(free_w_gb, 2) if free_w_gb is not None else None,
        }
    except Exception as e:
        return {
            "name": "Disk Capacity",
            "passed": False,
            "message": f"Disk check error: {e}",
            "free_c_gb": 0.0,
            "free_w_gb": None,
        }


def check_mcp_servers(workspace: Path) -> Dict[str, Any]:
    """Check 4: Checks enabled MCP server connectivity."""
    try:
        from diagnostics.doctor import SystemDoctor
        doctor = SystemDoctor(workspace=workspace)
        ok, msg = doctor.check_mcp_servers()
        return {
            "name": "MCP Server Connectivity",
            "passed": ok,
            "message": msg,
        }
    except Exception as e:
        return {
            "name": "MCP Server Connectivity",
            "passed": False,
            "message": f"MCP check error: {e}",
        }


def check_proactive_tasks(workspace: Path) -> Dict[str, Any]:
    """Check 5: Checks proactive scheduler configuration and task registration."""
    try:
        from diagnostics.doctor import SystemDoctor
        doctor = SystemDoctor(workspace=workspace)
        ok, msg = doctor.check_proactive_scheduler()
        return {
            "name": "Proactive Task Scheduler",
            "passed": ok,
            "message": msg,
        }
    except Exception as e:
        return {
            "name": "Proactive Task Scheduler",
            "passed": False,
            "message": f"Proactive scheduler error: {e}",
        }


def send_health_alert(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatches multi-channel alerts when a health check fails:
    1. Native Windows desktop notification toast via tools.notification_tool.
    2. SMTP email notification if credentials / recipient are configured.
    3. Persistent audit logging in logs/health_checks.log.
    """
    failing = result.get("failing_checks", [])
    failed_cnt = result.get("failed_count", 0)
    total_cnt = result.get("total_checks", 0)

    alert_title = f"⚠️ Orvix Health Alert: {failed_cnt}/{total_cnt} Checks Failed"
    fail_summary = ", ".join(failing) if failing else "System degraded"
    alert_msg = f"Health check failed at {result.get('timestamp')}. Failing: {fail_summary}."

    channels_dispatched = []

    # 1. Desktop Notification
    try:
        from tools.notification_tool import show_notification
        toast_res = show_notification(alert_title, alert_msg, duration_sec=8)
        if toast_res.get("status") == "SUCCESS":
            channels_dispatched.append("desktop_toast")
    except Exception as te:
        logger.warning(f"Toast notification dispatch failed: {te}")

    # 2. SMTP Email Alert (if configured in environment)
    alert_email_to = os.environ.get("ALERT_EMAIL_TO")
    smtp_server = os.environ.get("SMTP_SERVER")
    if alert_email_to and smtp_server:
        try:
            from tools.web_automation import email_client
            smtp_port = int(os.environ.get("SMTP_PORT", 587))
            smtp_user = os.environ.get("SMTP_USER")
            smtp_pass = os.environ.get("SMTP_PASS")

            body = (
                f"Orvix Sphere Health Alert\n"
                f"========================\n"
                f"Timestamp: {result.get('timestamp')}\n"
                f"Failed Checks: {failed_cnt}/{total_cnt}\n\n"
                f"Failing Areas:\n"
            )
            for chk in result.get("checks", []):
                if not chk.get("passed"):
                    body += f" - [X] {chk.get('name')}: {chk.get('message')}\n"
            body += "\nPlease review Orvix Sphere immediately or type /health in chat.\n"

            em_res = email_client(
                action="send",
                to_email=alert_email_to,
                subject=f"[Alert] Orvix Sphere System Health Degraded ({failed_cnt} failures)",
                body=body,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                username=smtp_user,
                password=smtp_pass,
                confirmed=True,
            )
            if em_res.get("status") == "SUCCESS":
                channels_dispatched.append("smtp_email")
            else:
                logger.warning(f"SMTP email dispatch notice: {em_res.get('error') or em_res.get('message')}")
        except Exception as ee:
            logger.warning(f"Email dispatch error: {ee}")
    else:
        logger.info("Email alert skipped: SMTP_SERVER / ALERT_EMAIL_TO not set in environment.")

    # 3. Persistent Log
    logger.warning(
        f"HEALTH ALERT DISPATCHED: {failed_cnt} failed checks ({fail_summary}). Channels: {channels_dispatched}"
    )

    return {
        "alert_sent": True,
        "channels": channels_dispatched,
        "title": alert_title,
        "message": alert_msg,
    }


def save_health_history(
    result: Dict[str, Any], history_file: Optional[Path] = None, max_history: int = 30
) -> None:
    """Saves a health check summary snapshot to logs/health_history.json (rolling)."""
    target = history_file or HEALTH_HISTORY_FILE
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        history: List[Dict[str, Any]] = []
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history = data
            except Exception:
                history = []

        entry = {
            "timestamp": result.get("timestamp"),
            "healthy": result.get("healthy"),
            "passed_checks": result.get("passed_checks"),
            "total_checks": result.get("total_checks"),
            "failed_checks": result.get("failing_checks", []),
            "error_count_24h": result.get("error_count_24h", 0),
            "free_c_gb": result.get("free_c_gb"),
            "alert_sent": result.get("alert_dispatched", False),
        }

        history.insert(0, entry)
        # Retain last max_history snapshots
        history = history[:max_history]

        with open(target, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save health history: {e}")


def get_health_history(limit: int = 7, history_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves the newest limit health check entries from history."""
    target = history_file or HEALTH_HISTORY_FILE
    if not target.exists():
        return []
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data[:limit]
            return []
    except Exception as e:
        logger.error(f"Failed to read health history: {e}")
        return []


def run_health_check(
    workspace: Optional[Path] = None,
    send_alert_on_failure: bool = True,
    force_alert: bool = False,
    history_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes all 5 core health checks:
    1. SystemDoctor full diagnostics
    2. 24h Error rate in logs/errors.db
    3. Disk capacity (C: and W:)
    4. MCP server availability
    5. Proactive task scheduler status

    If any check fails (or force_alert=True), dispatches multi-channel alerts.
    Persists audit entry in logs/health_checks.log and logs/health_history.json.
    """
    ws = Path(workspace).resolve() if workspace else BASE_DIR
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    checks: List[Dict[str, Any]] = [
        check_system_doctor(ws),
        check_recent_errors(ws, hours=24),
        check_disk_space(ws, min_gb=1.0),
        check_mcp_servers(ws),
        check_proactive_tasks(ws),
    ]

    total_checks = len(checks)
    passed_checks = sum(1 for c in checks if c.get("passed"))
    failing_checks = [c["name"] for c in checks if not c.get("passed")]
    failed_count = len(failing_checks)
    is_healthy = failed_count == 0

    # Extract auxiliary metrics for history
    err_count_24h = 0
    free_c_gb = None
    for c in checks:
        if c["name"] == "24h Error Rate":
            err_count_24h = c.get("error_count", 0)
        elif c["name"] == "Disk Capacity":
            free_c_gb = c.get("free_c_gb")

    result: Dict[str, Any] = {
        "timestamp": now_str,
        "healthy": is_healthy,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_count": failed_count,
        "failing_checks": failing_checks,
        "checks": checks,
        "error_count_24h": err_count_24h,
        "free_c_gb": free_c_gb,
        "alert_dispatched": False,
        "alert_details": None,
    }

    # Dispatch alerts if unhealthy or force_alert is set
    if (not is_healthy and send_alert_on_failure) or force_alert:
        alert_info = send_health_alert(result)
        result["alert_dispatched"] = True
        result["alert_details"] = alert_info

    # Log to audit log
    st_label = "HEALTHY" if is_healthy else f"UNHEALTHY ({failed_count} failing checks: {', '.join(failing_checks)})"
    logger.info(f"Daily health check executed: {st_label} [{passed_checks}/{total_checks} checks passed]")

    # Persist to health_history.json
    save_health_history(result, history_file=history_file)

    return result


def format_health_report(result: Dict[str, Any]) -> str:
    """Formats health check result into a clean diagnostic ASCII report."""
    lines = [
        "=" * 64,
        "            ORVIX SPHERE DAILY HEALTH CHECK REPORT              ",
        "=" * 64,
        f"Timestamp: {result.get('timestamp')}",
        f"Status:    {'[✓] ALL SYSTEMS HEALTHY' if result.get('healthy') else '[!] SYSTEM ATTENTION REQUIRED'}",
        "-" * 64,
    ]

    for c in result.get("checks", []):
        icon = "[✓]" if c.get("passed") else "[x]"
        lines.append(f"{icon} {c.get('name'):<26} : {c.get('message')}")

    lines.append("-" * 64)
    if result.get("healthy"):
        lines.append(f"Result: [✓] PASSED ({result.get('passed_checks')}/{result.get('total_checks')} checks verified)")
    else:
        lines.append(
            f"Result: [!] {result.get('failed_count')} CHECK(S) FAILED ({result.get('passed_checks')}/{result.get('total_checks')} passed)"
        )
        if result.get("alert_dispatched"):
            channels = result.get("alert_details", {}).get("channels", [])
            lines.append(f"Alert:  Dispatched via {', '.join(channels) if channels else 'desktop/log channels'}")

    lines.append("=" * 64)
    return "\n".join(lines)


def format_history_table(history: List[Dict[str, Any]]) -> str:
    """Formats health history into a clean tabular digest."""
    if not history:
        return "No historical health check records found in logs/health_history.json."

    lines = [
        "=" * 74,
        "               ORVIX SPHERE HEALTH CHECK HISTORY (LAST 7 DAYS)            ",
        "=" * 74,
        f"{'Date & Time (UTC)':<22} {'Status':<11} {'Passed':<8} {'24h Errors':<12} {'Disk Free':<11} {'Alert Sent'}",
        f"{'-'*22} {'-'*11} {'-'*8} {'-'*12} {'-'*11} {'-'*10}",
    ]

    for h in history:
        st = "HEALTHY" if h.get("healthy") else "UNHEALTHY"
        passed_str = f"{h.get('passed_checks', 0)}/{h.get('total_checks', 5)}"
        err_str = str(h.get("error_count_24h", 0))
        disk_str = f"{h.get('free_c_gb', 'N/A')} GB"
        alert_str = "Yes" if h.get("alert_sent") else "No"
        ts = str(h.get("timestamp", ""))[:21]
        lines.append(f"{ts:<22} {st:<11} {passed_str:<8} {err_str:<12} {disk_str:<11} {alert_str}")

    lines.append("=" * 74)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Orvix Sphere Daily Health Check & Alerting Engine")
    parser.add_argument("--alert", action="store_true", help="Force dispatch of desktop/email alerts regardless of health status")
    parser.add_argument("--history", action="store_true", help="Display the last 7 days of health checks from history")
    parser.add_argument("--limit", type=int, default=7, help="Number of history records to display")
    parser.add_argument("--quiet", action="store_true", help="Run silently without printing report (for background cron)")
    args = parser.parse_args()

    if args.history:
        history = get_health_history(limit=args.limit)
        print("\n" + format_history_table(history) + "\n")
        return 0

    res = run_health_check(force_alert=args.alert)
    if not args.quiet:
        print("\n" + format_health_report(res) + "\n")

    return 0 if res.get("healthy") else 1


if __name__ == "__main__":
    sys.exit(main())
