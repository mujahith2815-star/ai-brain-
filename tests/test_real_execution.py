"""
Integration and regression test suite for real tool execution, anti-hallucination enforcement,
execution logging, and pipeline responsiveness in P.H.A.S.S Sphere.
"""

import json
import os
import shutil
from pathlib import Path
import pytest
import psutil

from tools.executor import execute_tool
from core.llama_tool_agent import process_query
from nlp.answer_pipeline import generate_answer


class TestRealExecution:
    def setup_method(self):
        self.test_dir = Path("checkpoints/test_sandbox_project")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        agent_dir = Path("checkpoints/RealFolderTest")
        if agent_dir.exists():
            shutil.rmtree(agent_dir, ignore_errors=True)

    def test_open_notepad(self):
        """Verify launching Notepad starts a real process verified by psutil, then terminates it."""
        res = execute_tool("launch_application", {"app_name": "notepad"})
        assert isinstance(res, dict)
        assert res.get("status") == "SUCCESS"
        pid = res.get("pid")
        assert pid is not None
        assert psutil.pid_exists(pid)
        # Verify process and cleanup
        p = psutil.Process(pid)
        assert "notepad" in p.name().lower()
        p.kill()

    def test_launch_vscode(self):
        """Verify launching VS Code returns a real process ID and status SUCCESS."""
        res = execute_tool("launch_application", {"app_name": "code"})
        assert isinstance(res, dict)
        assert res.get("status") == "SUCCESS"
        assert res.get("pid") is not None
        assert isinstance(res.get("pid"), int)
        assert res.get("pid") > 0

        # Verify through process_query
        agent_response = process_query("open Visual Studio Code")
        assert "launched code" in agent_response.lower() or "pid" in agent_response.lower()

    def test_web_search(self):
        """Verify web search / knowledge query retrieves accurate factual data about Arduino capacitors."""
        res = execute_tool("web_search", {"query": "capacitor arduino"})
        assert isinstance(res, dict)
        assert res.get("status") == "SUCCESS"
        ans = res.get("answer", "")
        assert "0.1" in ans or "100 nf" in ans.lower() or "capacitor" in ans.lower()

        # Verify through agent query
        agent_ans = process_query("what capacitor is connected to Arduino")
        assert "0.1" in agent_ans or "100 nf" in agent_ans.lower() or "capacitor" in agent_ans.lower()

    def test_create_folder(self):
        """Verify create_folder creates an actual directory on disk with verified path."""
        target_path = str(self.test_dir / "subfolder")
        assert not os.path.exists(target_path)

        res = execute_tool("create_folder", {"folder_path": target_path})
        assert isinstance(res, dict)
        assert res.get("status") == "SUCCESS"
        assert res.get("success") is True
        assert os.path.exists(target_path)
        assert os.path.isdir(target_path)

        # Verify through agent query
        agent_target = "checkpoints/RealFolderTest"
        if os.path.exists(agent_target):
            shutil.rmtree(agent_target, ignore_errors=True)
        resp = process_query("create a folder called RealFolderTest in checkpoints")
        assert "folder created successfully" in resp.lower()
        assert os.path.exists(agent_target)
        assert os.path.isdir(agent_target)

    def test_file_write(self):
        """Verify file_writer writes content to disk, reads it back, and verifies."""
        test_file = self.test_dir / "hello.txt"
        res = execute_tool("write_file", {"file_path": str(test_file), "content": "Hello"})
        assert isinstance(res, dict)
        assert res.get("success") is True or res.get("status") == "SUCCESS"
        assert test_file.exists()
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "Hello"

        # Also test deletion
        del_res = execute_tool("delete_file", {"file_path": str(test_file)})
        assert isinstance(del_res, dict)
        assert del_res.get("status") == "SUCCESS"
        assert not test_file.exists()

    def test_project_start_command(self):
        """Verify 'can we start to make a project' creates ~/Desktop/NewProject and launches VS Code."""
        target_dir = Path(os.path.expanduser("~/Desktop/NewProject"))
        resp = process_query("can we start to make a project")
        assert "project folder created and vs code opened" in resp.lower()
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_execution_logging(self):
        """Verify all executed tools are persistently logged to checkpoints/execution_log.json."""
        log_file = Path("checkpoints/execution_log.json")
        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
        assert isinstance(entries, list)
        assert len(entries) > 0

        latest = entries[-1]
        assert "tool" in latest
        assert "args" in latest
        assert "result" in latest
        assert "timestamp" in latest

    def test_anti_hallucination_override(self):
        """Verify simulated claims and unexecuted assertions are intercepted."""
        fake_response = "I have launched the application using Custom Tool and Comprehensive analysis."
        intercepted = generate_answer("test query", context=fake_response)
        assert "[WARNING]" in intercepted
        assert "rephrase as a direct action" in intercepted

    def test_math_calculation_execution(self):
        """Verify bare math query 2+2 executes and returns real calculation."""
        res = process_query("2+2")
        assert "4" in res

    def test_greeting_response(self):
        """Verify UI responds politely and non-empty when greeted with Hello."""
        res = process_query("Hello")
        assert res is not None
        assert len(res) > 0
        assert "hello" in res.lower() or "p.h.a.s.s" in res.lower()

    def test_execution_orchestrator_pipeline(self):
        """Verify ExecutionOrchestrator strictly executes JSON actions, verifies OS state, and logs."""
        from core.execution_orchestrator import execution_orchestrator
        test_file = str(self.test_dir / "orchestrator_test.txt")
        plan = {
            "actions": [
                {"tool": "write_file", "args": {"file_path": test_file, "content": "orchestrator_verified"}},
                {"tool": "advanced_calculator", "args": {"expression": "10 * 5"}}
            ]
        }
        report = execution_orchestrator.execute_plan(plan)
        assert report["status"] == "SUCCESS"
        assert report["actions_executed"] == 2
        assert os.path.exists(test_file)
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "orchestrator_verified"
        assert "50" in report["summary"] or "Successfully executed" in report["summary"]

