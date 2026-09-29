"""
Unit Tests for P.H.A.S.S Voice Guardian Engine.
Verifies that:
1. Every time P.H.A.S.S starts up, core/voice_interface.py is scanned for syntax errors.
2. If a syntax error is found, Voice Guardian writes the fix.
3. Voice Guardian tests the fix via AST and bytecode compilation.
4. Voice Guardian restarts the voice service cleanly.
"""

import ast
import shutil
import tempfile
from pathlib import Path
import pytest

from core.voice_guardian import (
    VoiceGuardian,
    ensure_voice_interface_healthy,
    scan_voice_interface,
    fix_and_restart_voice,
)
from core.voice_interface import get_voice_interface, restart_voice_service, VoiceInterface


@pytest.fixture
def temp_voice_env(tmp_path):
    """Fixture providing an isolated environment with actual voice_interface.py code and golden baseline."""
    real_voice = Path("core/voice_interface.py").resolve()
    temp_voice = tmp_path / "voice_interface.py"
    shutil.copy2(str(real_voice), str(temp_voice))
    
    # Initialize guardian pointing to the temp file
    guardian = VoiceGuardian(voice_file=temp_voice)
    guardian.update_golden_baseline(force=True)
    return guardian, temp_voice


def test_voice_guardian_clean_scan():
    """Verify that current core/voice_interface.py has no syntax errors."""
    err = scan_voice_interface()
    assert err is None, f"Expected clean syntax in voice_interface.py, got error: {err}"


def test_voice_guardian_detects_missing_colon_syntax_error(temp_voice_env):
    """Verify that Voice Guardian detects a missing colon syntax error."""
    guardian, temp_voice = temp_voice_env
    
    # Inject deliberate syntax error (missing colon on def)
    lines = temp_voice.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if "def get_status(self)" in line:
            lines[i] = "    def get_status(self)"  # Missing colon!
            break
    temp_voice.write_text("\n".join(lines), encoding="utf-8")

    err = guardian.scan_syntax_errors(temp_voice)
    assert err is not None
    assert err["has_error"] is True
    assert "SyntaxError" in err["error_type"]
    assert "colon" in err["msg"].lower() or "expected" in err["msg"].lower()


def test_voice_guardian_fixes_and_tests_missing_colon(temp_voice_env):
    """Verify that Voice Guardian automatically fixes missing colon and tests it."""
    guardian, temp_voice = temp_voice_env

    # Inject missing colon
    lines = temp_voice.read_text(encoding="utf-8").splitlines()
    target_idx = None
    for i, line in enumerate(lines):
        if "def get_status(self)" in line:
            lines[i] = "    def get_status(self)"  # Missing colon!
            target_idx = i
            break
    temp_voice.write_text("\n".join(lines), encoding="utf-8")

    # Verify error is present before fix
    assert not guardian.test_fix(temp_voice)

    # Apply fix
    fixed = guardian.write_fix(temp_voice)
    assert fixed is True

    # Test fix
    test_passed = guardian.test_fix(temp_voice)
    assert test_passed is True

    # Ensure valid AST
    ast.parse(temp_voice.read_text(encoding="utf-8"))


def test_voice_guardian_fixes_unterminated_string_literal(temp_voice_env):
    """Verify that Voice Guardian fixes unterminated string literals."""
    guardian, temp_voice = temp_voice_env

    # Inject unterminated string
    content = temp_voice.read_text(encoding="utf-8")
    content += '\n_broken_debug_msg = "this is an unclosed string\n'
    temp_voice.write_text(content, encoding="utf-8")

    assert not guardian.test_fix(temp_voice)
    err = guardian.scan_syntax_errors(temp_voice)
    assert err is not None

    fixed = guardian.write_fix(temp_voice, err)
    assert fixed is True
    assert guardian.test_fix(temp_voice) is True


def test_voice_guardian_fallback_to_golden_on_severe_corruption(temp_voice_env):
    """Verify that Voice Guardian restores from golden baseline if corruption is severe."""
    guardian, temp_voice = temp_voice_env

    # Severely corrupt the file
    temp_voice.write_text("def %$$$ broken @@@ syntax !!! garbage", encoding="utf-8")
    assert not guardian.test_fix(temp_voice)

    # Apply repair
    guardian.ensure_voice_interface_healthy()

    # Verify restored and healthy
    assert guardian.test_fix(temp_voice) is True
    ast.parse(temp_voice.read_text(encoding="utf-8"))


def test_voice_guardian_restart_voice_service():
    """Verify that restarting the voice service yields an active VoiceInterface."""
    v1 = get_voice_interface()
    assert v1 is not None

    v2 = restart_voice_service()
    assert v2 is not None
    assert v2.__class__.__name__ == "VoiceInterface"
    assert hasattr(v2, "get_status")
    stat = v2.get_status()
    assert "is_listening" in stat
    assert "wake_word" in stat


def test_voice_guardian_startup_self_heal_routine():
    """Verify top-level ensure_voice_interface_healthy() runs cleanly on startup."""
    res = ensure_voice_interface_healthy()
    assert res["status"] in ("HEALTHY", "REPAIRED")
    assert "voice_interface" in res["message"].lower()
