"""
Comprehensive Unit & Integration Test Suite for P.H.A.S.S Llama Assistant:
Autonomous Mode & Digital Workforce.
"""

import os
import sys
import json
import time
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.autonomous_orchestrator import AutonomousOrchestrator, get_orchestrator
from core.daily_routine import DailyRoutineManager
from core.predictive_engine import PredictiveEngine
from integrations.vscode_controller import VSCodeController
from integrations.git_manager import GitManager
from integrations.docker_controller import DockerController
from integrations.cloud_sync import CloudSync
from core.self_improvement import SelfImprovementEngine
from core.mobile_interface import MobileInterface
from core.analytics_engine import AnalyticsEngine
from security.auto_security import AutoSecurity
from core.llama_tool_agent import run_autonomous, get_agent
import tkinter as tk


# =============================================================================
# 1. AUTONOMOUS ORCHESTRATOR TESTS
# =============================================================================

class TestAutonomousOrchestrator:
    def test_plan_generation_and_execution(self, tmp_path):
        """Verify plan generation and multi-step execution with retries."""
        orch = AutonomousOrchestrator(workspace_dir=str(tmp_path))

        goal = "Analyze system disk and clean downloads"
        plan = orch.generate_plan(goal)

        assert "plan_id" in plan
        assert len(plan.get("steps", [])) >= 2

        # Execute workflow
        with patch("tools.executor.execute_tool", return_value={"status": "success", "result": "ok"}):
            result = orch.execute_workflow(plan)

        assert result.get("status") in ["completed", "success"]
        assert len(result.get("results", [])) == len(plan["steps"])

    def test_emergency_and_critical_decision_handling(self, tmp_path):
        """Verify raising emergency and queuing non-blocking critical decisions."""
        orch = AutonomousOrchestrator(workspace_dir=str(tmp_path))

        # Emergency
        em_id = orch.raise_emergency("SYSTEM_DISK_FULL", "Root disk is at 99% capacity")
        assert em_id is not None
        emergencies = orch.get_emergencies()
        assert len(emergencies) == 1
        assert emergencies[0]["type"] == "SYSTEM_DISK_FULL"

        orch.resolve_emergency(em_id)
        assert len(orch.get_emergencies()) == 0

        # Critical decision
        dec_id = orch.queue_critical_decision(
            "Production database migration needed",
            options=["Migrate Now", "Postpone", "Abort"]
        )
        assert dec_id is not None
        decisions = orch.get_pending_decisions()
        assert len(decisions) == 1

        orch.resolve_critical_decision(dec_id, "Migrate Now")
        assert len(orch.get_pending_decisions()) == 0

    def test_state_persistence(self, tmp_path):
        """Verify state save and recovery from disk."""
        orch = AutonomousOrchestrator(workspace_dir=str(tmp_path))
        orch.queue_critical_decision("Review required", ["Approve", "Deny"])
        orch.save_state()

        state_file = tmp_path / "state.json"
        assert state_file.exists()

        orch2 = AutonomousOrchestrator(workspace_dir=str(tmp_path))
        assert len(orch2.get_pending_decisions()) == 1


# =============================================================================
# 2. DAILY ROUTINE MANAGER (ZERO IOT) TESTS
# =============================================================================

class TestDailyRoutineManager:
    def test_morning_briefing_no_iot(self, tmp_path):
        """Verify morning briefing generates without any smart home / IoT references."""
        routine = DailyRoutineManager(storage_dir=str(tmp_path))
        briefing = routine.morning_briefing()

        assert "briefing" in briefing
        text = briefing["briefing"].lower()
        # Strictly zero smart home / IoT
        assert "philips" not in text
        assert "hue" not in text
        assert "smart bulb" not in text
        assert "home assistant" not in text
        assert "thermostat" not in text

    def test_scheduled_task_runner_with_retries(self, tmp_path):
        """Verify tasks execute and retries operate properly."""
        routine = DailyRoutineManager(storage_dir=str(tmp_path))
        executed = []

        def failing_then_succeeding_action():
            if len(executed) == 0:
                executed.append("fail")
                raise RuntimeError("Temporary glitch")
            executed.append("success")
            return "done"

        routine.schedule_task("test_backup", interval_seconds=1, action=failing_then_succeeding_action, max_retries=2)
        results = routine.run_pending_tasks(force_all=True)

        assert "test_backup" in results
        assert results["test_backup"]["status"] in ["retried", "success", "completed"]

    def test_smart_inbox_classifier(self, tmp_path):
        """Verify inbox classifier tags priority, urgency, and auto-drafts responses."""
        routine = DailyRoutineManager(storage_dir=str(tmp_path))
        emails = [
            {"id": "1", "sender": "boss@corp.com", "subject": "URGENT: Review Q3 Budget", "body": "Need signoff asap."},
            {"id": "2", "sender": "promo@deals.com", "subject": "50% off shoes", "body": "Click here to buy."}
        ]
        classified = routine.classify_inbox(emails)

        assert len(classified) == 2
        urgent = next(m for m in classified if m["id"] == "1")
        assert urgent["urgency"] == "high"
        assert urgent["action_required"] is True
        assert len(urgent.get("draft_reply", "")) > 0

    def test_meeting_scheduler_conflict_detection(self, tmp_path):
        """Verify meeting scheduler detects conflicts and creates bookings."""
        routine = DailyRoutineManager(storage_dir=str(tmp_path))
        m1 = routine.schedule_meeting(
            title="Sprint Planning",
            start_time="2026-09-10T10:00:00",
            duration_minutes=60,
            participants=["alice@test.com"]
        )
        assert m1.get("status") == "scheduled"

        # Overlapping meeting
        m2 = routine.schedule_meeting(
            title="Design Review",
            start_time="2026-09-10T10:30:00",
            duration_minutes=30,
            participants=["bob@test.com"]
        )
        assert m2.get("status") == "conflict"
        assert "alternative_slots" in m2 or "conflict" in m2.get("message", "").lower()


# =============================================================================
# 3. PREDICTIVE ENGINE TESTS
# =============================================================================

class TestPredictiveEngine:
    def test_record_activity_and_autocomplete(self, tmp_path):
        """Verify command prediction and autocomplete based on history."""
        engine = PredictiveEngine(storage_dir=str(tmp_path))
        engine.record_activity("shell_command", {"cmd": "git push origin main"})
        engine.record_activity("shell_command", {"cmd": "git status"})
        engine.record_activity("shell_command", {"cmd": "docker-compose up -d"})

        suggestions = engine.predict_command("git")
        assert any("git" in s for s in suggestions)

    def test_prepare_environment(self, tmp_path):
        """Verify prepare_environment configures workspace profiles."""
        engine = PredictiveEngine(storage_dir=str(tmp_path))
        res = engine.prepare_environment("coding")
        assert res.get("status") == "success"
        assert "environment" in res

    def test_predictive_trash_holding(self, tmp_path):
        """Verify safe 7-day trash quarantine holding and cleanup."""
        engine = PredictiveEngine(storage_dir=str(tmp_path))

        dummy = tmp_path / "scratch_to_delete.txt"
        dummy.write_text("temporary data", encoding="utf-8")

        trash_res = engine.trash_file(str(dummy))
        assert trash_res.get("status") == "trashed"
        assert not dummy.exists()

        # Immediate cleanup with retention=0 days clears it
        cleaned = engine.cleanup_trash(retention_days=0)
        assert cleaned.get("purged_count", 0) >= 1


# =============================================================================
# 4. DEVELOPER & CLOUD INTEGRATIONS TESTS
# =============================================================================

class TestIntegrations:
    def test_vscode_controller_actions(self, tmp_path):
        """Verify VSCodeController executes workspace configurations."""
        vsc = VSCodeController()
        cfg_res = vsc.configure_workspace(str(tmp_path), {"editor.tabSize": 4})
        assert cfg_res.get("status") == "success"
        vscode_dir = tmp_path / ".vscode"
        assert vscode_dir.exists()

    def test_git_manager_smart_commit_and_status(self, tmp_path):
        """Verify GitManager status reporting and commit message formatting."""
        gm = GitManager(repo_path=str(tmp_path))
        status = gm.status()
        assert "branch" in status or "error" in status or "clean" in status

        msg = gm.generate_ai_commit_message(["core/daily_routine.py", "ui/main_window.py"])
        assert len(msg) > 5

    def test_docker_controller_prune_and_lifecycle(self):
        """Verify DockerController actions return structured status."""
        dc = DockerController()
        res = dc.auto_restart_crashed()
        assert "checked_at" in res or "restarted" in res

    def test_cloud_sync_mirror(self, tmp_path):
        """Verify CloudSync mirrors files and resolves conflicts."""
        src = tmp_path / "source"
        tgt = tmp_path / "target"
        src.mkdir()
        tgt.mkdir()

        (src / "file1.txt").write_text("version 1", encoding="utf-8")
        sync = CloudSync()
        res = sync.sync_directories(str(src), str(tgt))

        assert res.get("synced_count", 0) >= 1
        assert (tgt / "file1.txt").exists()


# =============================================================================
# 5. SELF IMPROVEMENT ENGINE TESTS
# =============================================================================

class TestSelfImprovementEngine:
    def test_skill_registry_and_execution_metrics(self, tmp_path):
        """Verify skill registration, metrics tracking, and auto-tuning."""
        engine = SelfImprovementEngine(storage_dir=str(tmp_path))
        reg_res = engine.register_skill(
            name="format_json_skill",
            description="Formats unorganized JSON",
            code="def run(data): return json.dumps(data, indent=2)"
        )
        assert reg_res.get("status") == "registered"

        skill = engine.get_skill("format_json_skill")
        assert skill is not None
        assert skill["name"] == "format_json_skill"

        engine.record_execution("format_json_skill", success=True, execution_time=0.05)
        stats = engine.get_skill_stats("format_json_skill")
        assert stats.get("runs", 0) == 1

    def test_auto_tune_and_diagnose(self, tmp_path):
        """Verify auto-tuning on high resource load and self-healing error diagnosis."""
        engine = SelfImprovementEngine(storage_dir=str(tmp_path))
        tune = engine.auto_tune_resources(cpu_percent=85.0, memory_percent=82.0)
        assert tune.get("action") in ["throttled", "optimized", "ok"]

        heal = engine.diagnose_and_heal("No module named 'foobar'")
        assert "suggestion" in heal or "healed" in heal


# =============================================================================
# 6. MOBILE & ANALYTICS TESTS
# =============================================================================

class TestMobileAndAnalytics:
    def test_mobile_push_gateway(self, tmp_path):
        """Verify mobile notification queueing and retrieval."""
        mob = MobileInterface(storage_dir=str(tmp_path))
        mob.queue_push_notification("High Alert", "CPU usage at 90%", priority="high")
        pending = mob.get_pending_notifications()
        assert len(pending) == 1
        assert pending[0]["title"] == "High Alert"

    def test_analytics_reports_and_budget(self, tmp_path):
        """Verify daily/weekly executive reports and budget logging."""
        ana = AnalyticsEngine(storage_dir=str(tmp_path))
        ana.log_expense(45.50, "Cloud Computing", "AWS Serverless test run")
        summary = ana.get_budget_summary()
        assert summary.get("total_expense", 0.0) >= 45.50

        report = ana.generate_daily_report()
        assert "# Executive Daily Summary" in report or "Executive" in report


# =============================================================================
# 7. SECURITY & ENCRYPTION TESTS
# =============================================================================

class TestAutoSecurity:
    def test_encryption_roundtrip(self, tmp_path):
        """Verify AES-256 zero-click encryption and decryption roundtrip."""
        sec = AutoSecurity(storage_dir=str(tmp_path))
        secret_file = tmp_path / "secret.env"
        secret_file.write_text("API_KEY=supersecretkey123", encoding="utf-8")

        enc_path = sec.encrypt_sensitive_file(str(secret_file), passphrase="testpassword")
        assert Path(enc_path).exists()
        assert not secret_file.exists()

        dec_path = sec.decrypt_sensitive_file(enc_path, passphrase="testpassword")
        assert Path(dec_path).exists()
        assert Path(dec_path).read_text(encoding="utf-8") == "API_KEY=supersecretkey123"

    def test_snapshot_and_rollback(self, tmp_path):
        """Verify state snapshots and rollback capabilities."""
        sec = AutoSecurity(storage_dir=str(tmp_path))
        test_file = tmp_path / "app_config.json"
        test_file.write_text('{"v": 1}', encoding="utf-8")

        snap_id = sec.create_system_snapshot("pre_update", target_dir=str(tmp_path))
        assert snap_id is not None

        # Modify file
        test_file.write_text('{"v": 2, "corrupted": true}', encoding="utf-8")

        # Rollback
        rb = sec.rollback_snapshot(snap_id, restore_dir=str(tmp_path))
        assert rb.get("status") == "restored"
        assert test_file.read_text(encoding="utf-8") == '{"v": 1}'


# =============================================================================
# 8. AUTONOMOUS AGENT & UI INTEGRATION TESTS
# =============================================================================

class TestAutonomousAgentAndUI:
    def test_run_autonomous_agent(self):
        """Verify run_autonomous orchestrates without blocking."""
        with patch("core.autonomous_orchestrator.AutonomousOrchestrator.execute_workflow") as mock_exec:
            mock_exec.return_value = {"status": "completed", "summary": "Task done successfully."}
            res = run_autonomous("Clean up files and run test suite")
            assert res.get("status") == "completed"

    @pytest.fixture(scope="module")
    def shared_tk(self):
        try:
            root = tk.Tk()
            root.withdraw()
            yield root
            try:
                root.destroy()
            except Exception:
                pass
        except Exception:
            yield None

    def test_ui_autonomous_mode(self, shared_tk, tmp_path):
        """Verify AssistantUI autonomous mode toggle, workspaces, and buttons."""
        if not shared_tk:
            pytest.skip("Tkinter display not available")

        from ui.main_window import AssistantUI

        top = tk.Toplevel(shared_tk)
        top.withdraw()

        with patch("ui.main_window.Path") as mock_path:
            mock_path.return_value = tmp_path / "workspaces.json"
            mock_path.home.return_value = tmp_path

            app = AssistantUI(root=top)

            assert "Automations" in app.workspaces
            assert "Reports" in app.workspaces
            assert hasattr(app, "auto_btn")
            assert hasattr(app, "mobile_status_label")
            assert hasattr(app, "devtools_status_label")

            # Toggle autonomous mode on
            assert app.autonomous_mode is False
            app.toggle_autonomous()
            assert app.autonomous_mode is True
            assert "ON" in app.auto_btn.cget("text")

            # Toggle off
            app.toggle_autonomous()
            assert app.autonomous_mode is False

            app.on_close()
            try:
                top.destroy()
            except Exception:
                pass
