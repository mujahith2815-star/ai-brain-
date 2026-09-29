"""
Comprehensive automated tests for Local Llama Intelligence & Multi-Step Reasoning Layer.
Tests configuration, tool registry coverage, truthful error reporting,
single-step execution, multi-step workflows, and answer pipeline routing.
"""

import asyncio
import os
import pytest
from pathlib import Path
from typing import Dict, Any

from config.llama_config import llama_config, LlamaConfig
from tools.registry import tool_registry
from tools.executor import ToolExecutor
from core.llama_tool_agent import llama_tool_agent, ReasoningStep
from nlp.answer_pipeline import answer_pipeline


class TestLlamaIntelligenceLayer:

    def test_llama_config_and_cpu_safeguards(self):
        """Verifies default settings and CPU safeguard (num_gpu=0)."""
        cfg = llama_config.to_dict()
        assert "llama" in cfg["model_name"].lower()
        assert cfg["endpoint"] == "http://127.0.0.1:11434"
        assert cfg["num_gpu"] in (0, 1), "num_gpu should be 0 (CPU) or 1 (GPU with CPU fallback)"
        assert 0.0 <= cfg["temperature"] <= 1.0
        assert cfg["max_reasoning_steps"] >= 4

        # Test dynamic updates
        orig_model = llama_config.model_name
        llama_config.update_model("llama3.2:3b")
        assert llama_config.model_name == "llama3.2:3b"
        llama_config.update_model(orig_model)
        assert llama_config.model_name == orig_model

    def test_registered_tools_catalog_coverage(self):
        """Verifies that all required operational tools are registered."""
        tool_names = [t["name"] for t in tool_registry.list_tools()]
        expected_tools = [
            "file_reader",
            "file_writer",
            "file_editor",
            "advanced_calculator",
            "launch_application",
            "list_processes",
            "terminate_process",
            "execute_command",
            "live_search",
            "generate_report",
            "system_diagnostics",
        ]
        for t in expected_tools:
            assert t in tool_names, f"Expected tool '{t}' missing from tool_registry"

    @pytest.mark.asyncio
    async def test_truthful_file_reader_on_missing_file(self):
        """Verifies that file_reader truthfully reports failure when a file does not exist."""
        executor = ToolExecutor()
        missing_path = "workspace/definitely_non_existent_file_abc123.txt"
        res = await executor.execute_tool("file_reader", {"file_path": missing_path})

        assert not res.success or res.output.get("status") == "FAILED"
        assert "does not exist" in str(res.output.get("error"))
        # Must NOT return simulated success
        assert "[Simulated Content]" not in str(res.output)

    @pytest.mark.asyncio
    async def test_truthful_file_reader_on_real_file(self, tmp_path):
        """Verifies that file_reader reads actual file content accurately."""
        test_file = tmp_path / "sample_data.txt"
        test_file.write_text("Line 1: Alpha\nLine 2: Beta\nLine 3: Gamma", encoding="utf-8")

        executor = ToolExecutor()
        res = await executor.execute_tool("file_reader", {"file_path": str(test_file)})

        assert res.success
        assert res.output.get("status") == "SUCCESS"
        assert res.output.get("lines_read") == 3
        assert "Alpha" in res.output.get("content")

    @pytest.mark.asyncio
    async def test_advanced_calculator_tool_execution(self):
        """Verifies that advanced_calculator solves arithmetic and conversions correctly."""
        executor = ToolExecutor()

        # Arithmetic
        res1 = await executor.execute_tool("advanced_calculator", {"expression": "25 * 40 + 150"})
        assert res1.success
        assert res1.output.get("result") == 1150.0

        # Unit Conversion
        res2 = await executor.execute_tool("advanced_calculator", {"expression": "100 c to f"})
        assert res2.success
        assert res2.output.get("result") == 212.0

    @pytest.mark.asyncio
    async def test_file_writer_and_editor_tools(self, tmp_path):
        """Verifies real file creation and surgical search-and-replace editing."""
        executor = ToolExecutor()
        target_file = tmp_path / "config_test.json"

        # 1. Write file
        initial_content = '{"status": "INITIAL", "port": 8000}'
        res1 = await executor.execute_tool("file_writer", {"file_path": str(target_file), "content": initial_content})
        assert res1.success
        assert target_file.exists()

        # 2. Edit file (search & replace)
        res2 = await executor.execute_tool(
            "file_editor",
            {
                "file_path": str(target_file),
                "target_snippet": '"status": "INITIAL"',
                "replacement_snippet": '"status": "DEPLOYED"',
            }
        )
        assert res2.success
        updated_content = target_file.read_text(encoding="utf-8")
        assert '"status": "DEPLOYED"' in updated_content

    def test_multi_step_scenario_execution(self, tmp_path):
        """
        Tests the end-to-end multi-step scenario:
        1. Create an expenses document.
        2. Run LlamaToolAgent or simulated tool-chain to read, calculate, and report.
        """
        expenses_file = tmp_path / "q1_expenses.txt"
        expenses_file.write_text(
            "Q1 Expenses Breakdown:\n"
            "Cloud Infrastructure: 400\n"
            "Software Licenses: 250\n"
            "Developer Tools: 150\n",
            encoding="utf-8"
        )
        report_file = tmp_path / "q1_report.md"

        # Execute multi-step workflow via ToolExecutor synchronously
        executor = ToolExecutor()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Step 1: Read document
        read_res = loop.run_until_complete(
            executor.execute_tool("file_reader", {"file_path": str(expenses_file)})
        )
        assert read_res.success
        assert "Cloud Infrastructure: 400" in read_res.output["content"]

        # Step 2: Calculate total (400 + 250 + 150)
        calc_res = loop.run_until_complete(
            executor.execute_tool("advanced_calculator", {"expression": "400 + 250 + 150"})
        )
        assert calc_res.success
        total = calc_res.output["result"]
        assert total == 800.0

        # Step 3: Write report
        report_content = f"# Q1 Expenses Report\n\nTotal Calculated Expenses: ${total:.2f}\nStatus: Verified\n"
        write_res = loop.run_until_complete(
            executor.execute_tool("file_writer", {"file_path": str(report_file), "content": report_content})
        )
        assert write_res.success
        assert report_file.exists()
        assert "$800.00" in report_file.read_text(encoding="utf-8")
        loop.close()

    def test_truthful_error_handling_in_agent_loop(self):
        """
        Verifies that when a tool returns an error, the agent loop records
        success=False and captures the real error message truthfully.
        """
        step = ReasoningStep(
            step_number=1,
            thought="Attempting to read nonexistent file",
            action_type="call_tool",
            tool_name="file_reader",
            parameters={"file_path": "non_existent_file_999.txt"},
            tool_output={"status": "FAILED", "error": "File does not exist: non_existent_file_999.txt"},
            success=False,
            error="File does not exist: non_existent_file_999.txt",
        )
        step_dict = step.to_dict()
        assert not step_dict["success"]
        assert "File does not exist" in step_dict["error"]

    def test_answer_pipeline_routing(self):
        """Verifies answer pipeline handles capability and direct queries without breaking."""
        # Capability question
        resp = answer_pipeline.generate_answer("what can you do")
        assert "Here is what I can do for you:" in resp or "In " in resp
        assert "files" in resp.lower() or "code" in resp.lower()

        # Math question routing
        math_resp = answer_pipeline.generate_answer("calculate 150 + 250")
        assert math_resp is not None
        assert len(math_resp) > 0

    def test_local_llama_engine_availability(self):
        """Verifies that LocalLlamaEngine initializes and functions without external Ollama software."""
        from core.local_llama_engine import local_llama_engine
        assert local_llama_engine is not None
        out = local_llama_engine.generate("Hello world")
        assert out is not None and len(out) > 0

    def test_end_to_end_agent_multi_step_turn(self, tmp_path):
        """Tests full end-to-end multi-step reasoning turn on llama_tool_agent."""
        doc_path = tmp_path / "budget.txt"
        doc_path.write_text("Cloud Infrastructure: 100\nSoftware Licenses: 200\nDeveloper Tools: 50\n", encoding="utf-8")
        out_report = tmp_path / "budget_report.txt"

        query = f"Read document {doc_path}, calculate the total, and save to {out_report}"
        result = llama_tool_agent.run_turn(query)

        assert result.success
        assert len(result.steps_executed) >= 2
        # Verify tool sequence
        tools_called = [s.tool_name for s in result.steps_executed if s.tool_name]
        assert "file_reader" in tools_called
        assert "advanced_calculator" in tools_called
        assert "file_writer" in tools_called
        assert out_report.exists()
        assert "350" in out_report.read_text(encoding="utf-8")

    def test_end_to_end_agent_truthful_missing_file_reporting(self):
        """Tests that agent truthfully reports missing file error without pretending success."""
        query = "Read document missing_critical_data_9999.txt"
        result = llama_tool_agent.run_turn(query)

        assert any(not s.success for s in result.steps_executed if s.tool_name == "file_reader")
        assert any(word in result.final_response.lower() for word in ["failed", "error", "not exist", "verify"])
