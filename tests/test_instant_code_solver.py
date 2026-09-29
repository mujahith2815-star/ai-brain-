"""
Unit & Integration Tests for Instant Autonomous Code Generator & Problem Solver.
"""

import os
import pytest
from tools.instant_code_solver import instant_code_solver
from nlp.conversational_agent import conversational_agent


# 1. Trigger Detection
def test_code_request_detection():
    assert instant_code_solver.is_code_or_solve_request("wright a code for positive integer finder") is True
    assert instant_code_solver.is_code_or_solve_request("write code for fibonacci") is True
    assert instant_code_solver.is_code_or_solve_request("python code for quicksort") is True
    assert instant_code_solver.is_code_or_solve_request("hello how are you") is False


# 2. Code Generation & Execution Sanity
def test_positive_integer_finder_generation():
    sol = instant_code_solver.solve_and_generate_code("wright a code for positive integer finder")
    assert "def find_positive_integers" in sol.code_content
    assert os.path.exists(sol.file_path)

    # Test generated code execution dynamically
    local_ns = {}
    exec(sol.code_content, {}, local_ns)
    assert "find_positive_integers" in local_ns
    fn = local_ns["find_positive_integers"]
    res = fn([-5, 0, 10, "25", -3.2, 7])
    assert res == [10, 25, 7]


# 3. Conversational Natural Language Routing
def test_conversational_instant_code_generation():
    # User's exact prompt
    prompt = "wright a code for positive integer finder"
    res = conversational_agent.handle_natural_conversation(prompt)

    assert res is not None
    assert res["handled"] is True
    assert res["type"] == "AUTONOMOUS_CODE_GENERATION"
    assert "find_positive_integers" in res["speech_text"]
    assert "```python" in res["speech_text"]
