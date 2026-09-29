"""
SystemDoctor - Comprehensive Health & Diagnostic Suite for Orvix Sphere.
Validates Python runtime, packages, models, databases, MCP, voice, and system permissions.
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class CheckList(list):
    """List of check dictionaries that also allows dictionary-like key access."""
    def get(self, key: str, default=None):
        key_norm = key.lower().replace(" ", "_")
        for item in self:
            item_key = item.get("check", "").lower().replace(" ", "_")
            if item_key == key_norm or key_norm in item_key:
                return item.get("message")
        return default


class SystemDoctor:
    """
    Runs comprehensive diagnostic checks on all Orvix Sphere subsystems.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()

    def check_python_version(self) -> Tuple[bool, str]:
        major, minor = sys.version_info[:2]
        if major >= 3 and minor >= 10:
            return (True, f"Python {major}.{minor}.{sys.version_info.micro} (>= 3.10 required)")
        return (False, f"Python {major}.{minor} is below minimum requirement of 3.10")

    def check_required_packages(self) -> Tuple[bool, str]:
        required = ["fastapi", "uvicorn", "jinja2", "rich", "psutil", "apscheduler", "watchdog"]
        missing = []
        for pkg in required:
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
        if not missing:
            return (True, "All core production dependencies installed")
        return (False, f"Missing packages: {', '.join(missing)}")

    def check_sqlite_db(self) -> Tuple[bool, str]:
        db_path = self.workspace / "knowledge" / "agent_memory.db"
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT 1")
            conn.close()
            return (True, f"Database accessible ({db_path.name})")
        except Exception as e:
            return (False, f"Database error: {e}")

    def check_disk_space(self, min_gb: float = 1.0) -> Tuple[bool, str]:
        try:
            usage = shutil.disk_usage(str(self.workspace))
            free_gb = usage.free / (1024 ** 3)
            if free_gb >= min_gb:
                return (True, f"{free_gb:.2f} GB disk space free (>= {min_gb} GB required)")
            return (False, f"Low disk space: {free_gb:.2f} GB free")
        except Exception as e:
            return (False, f"Disk check error: {e}")

    def check_write_permissions(self) -> Tuple[bool, str]:
        test_file = self.workspace / ".doctor_write_test"
        try:
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return (True, "Workspace directory is writable")
        except Exception as e:
            return (False, f"No write permission: {e}")

    def check_vector_store(self) -> Tuple[bool, str]:
        try:
            from knowledge.vector_store import VectorStore
            vs = VectorStore()
            if vs.check_persistence():
                count = vs.num_documents()
                return (True, f"Vector Storage: {count} documents persisted (round-trip OK)")
            else:
                return (False, "Vector Storage: FAILED (persistence broken)")
        except Exception as e:
            return (False, f"Vector Storage: FAILED ({e})")

    def check_mcp_servers(self) -> Tuple[bool, str]:
        try:
            import time
            from mcp.mcp_manager import MCPManager
            m = MCPManager()
            m.start_all()
            enabled_servers = [name for name, c in m.clients.items() if c.config.enabled]
            total = len(enabled_servers)

            connected = 0
            for _ in range(12):
                time.sleep(0.5)
                connected = sum(1 for name in enabled_servers if m.clients[name].is_connected)
                if connected == total and total > 0:
                    break

            if connected == total and total > 0:
                return (True, f"MCP: {connected}/{total} servers online")
            elif connected > 0:
                failed = total - connected
                return (True, f"MCP: {connected}/{total} online ({failed} failed)")
            else:
                return (False, f"MCP: 0/{total} online (All failed to connect)")
        except Exception as e:
            return (False, f"MCP connection error: {e}")

    def check_proactive_scheduler(self) -> Tuple[bool, str]:
        try:
            from proactive.scheduler import TaskScheduler
            s = TaskScheduler()
            if not s.list_tasks():
                triggers_file = self.workspace / "proactive" / "triggers.json"
                if triggers_file.exists():
                    s.bootstrap_from_triggers(str(triggers_file))
            tasks = s.list_tasks()
            total = len(tasks)
            enabled = sum(1 for t in tasks if t.get("enabled", True))
            if total > 0:
                return (True, f"Proactive Scheduler: {total} tasks registered ({enabled} enabled)")
            return (True, "Proactive Scheduler: 0 tasks (check triggers.json)")
        except Exception as e:
            return (False, f"Scheduler error: {e}")

    def check_models(self) -> Tuple[bool, str]:
        try:
            from config.llama_config import llama_config
            return (True, f"Configured model: {llama_config.model_name} (Provider: {llama_config.provider})")
        except Exception as e:
            return (False, f"Model configuration error: {e}")

    def run_full_check(self) -> Dict[str, Any]:
        """Runs all checks and compiles a diagnostic report."""
        checks = [
            ("Python Runtime", self.check_python_version),
            ("Dependencies", self.check_required_packages),
            ("Database Access", self.check_sqlite_db),
            ("Disk Capacity", self.check_disk_space),
            ("Write Permissions", self.check_write_permissions),
            ("Vector Storage", self.check_vector_store),
            ("MCP Servers", self.check_mcp_servers),
            ("Proactive Scheduler", self.check_proactive_scheduler),
            ("Model Configuration", self.check_models),
        ]

        results = CheckList()
        overall_healthy = True
        for name, fn in checks:
            ok, msg = fn()
            if not ok:
                overall_healthy = False
            results.append({
                "check": name,
                "passed": ok,
                "message": msg,
                "icon": "[✓]" if ok else "[x]"
            })

        return {
            "healthy": overall_healthy,
            "checks": results,
            "total_checks": len(checks),
            "passed_checks": sum(1 for r in results if r["passed"]),
        }

    def format_report(self) -> str:
        report = self.run_full_check()
        lines = [
            "=" * 60,
            "          ORVIX SPHERE SYSTEM HEALTH DIAGNOSTIC REPORT        ",
            "=" * 60,
        ]
        for r in report["checks"]:
            lines.append(f"{r['icon']} {r['check']:<22} : {r['message']}")
        lines.append("-" * 60)
        status_line = "[✓] ALL SYSTEMS OPERATIONAL" if report["healthy"] else "[!] WARNINGS DETECTED"
        lines.append(f"Result: {status_line} ({report['passed_checks']}/{report['total_checks']} Passed)")
        lines.append("=" * 60)
        return "\n".join(lines)
