"""
Voice Guardian Engine for P.H.A.S.S Sphere.
Monitors, scans, and auto-repairs syntax errors in core/voice_interface.py at startup.
If a syntax error is detected:
1. Scans and isolates the exact syntax/indentation fault.
2. Writes the fix using AST/heuristic analysis and golden baseline fallback.
3. Tests the fix through compilation and AST parsing.
4. Restarts the voice service seamlessly.
"""

from __future__ import annotations
import ast
import importlib
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("phass.core.voice_guardian")

DEFAULT_VOICE_FILE = Path(__file__).parent / "voice_interface.py"
GOLDEN_BACKUP_FILE = Path(__file__).parent / "voice_interface.py.golden"
CORRUPT_BACKUP_FILE = Path(__file__).parent / "voice_interface.py.corrupted"


class VoiceGuardian:
    def __init__(self, voice_file: Optional[Path] = None):
        self.voice_file = Path(voice_file or DEFAULT_VOICE_FILE).resolve()
        self.golden_file = self.voice_file.with_name(self.voice_file.name + ".golden")
        self.corrupt_file = self.voice_file.with_name(self.voice_file.name + ".corrupted")
        self.last_scan_result: Optional[Dict[str, Any]] = None

    # ==================== 1. SCAN ====================

    def scan_syntax_errors(self, target_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """
        Scans target file for syntax or indentation errors using AST parsing and compilation.
        Returns None if clean, or a dict detailing the syntax error.
        """
        filepath = Path(target_path or self.voice_file)
        if not filepath.exists():
            return {
                "has_error": True,
                "error_type": "FileNotFoundError",
                "msg": f"Target file does not exist: {filepath}",
                "lineno": 1,
                "offset": 0,
                "text": "",
            }

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {
                "has_error": True,
                "error_type": "ReadError",
                "msg": f"Failed to read file: {e}",
                "lineno": 1,
                "offset": 0,
                "text": "",
            }

        # 1. AST Parsing Check
        try:
            ast.parse(source, filename=str(filepath))
        except (SyntaxError, IndentationError) as err:
            err_info = {
                "has_error": True,
                "error_type": type(err).__name__,
                "msg": str(err.msg),
                "lineno": err.lineno or 1,
                "offset": err.offset or 0,
                "text": err.text or "",
            }
            self.last_scan_result = err_info
            return err_info

        # 2. Bytecode Compilation Check
        try:
            compile(source, str(filepath), "exec")
        except (SyntaxError, IndentationError) as err:
            err_info = {
                "has_error": True,
                "error_type": type(err).__name__,
                "msg": str(err.msg),
                "lineno": err.lineno or 1,
                "offset": err.offset or 0,
                "text": err.text or "",
            }
            self.last_scan_result = err_info
            return err_info

        self.last_scan_result = None
        return None

    # ==================== 2. WRITE FIX ====================

    def write_fix(
        self,
        target_path: Optional[Path] = None,
        error_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Writes an automated fix for the detected syntax error in the target file.
        Attempts localized heuristic repair first; falls back to golden baseline if needed.
        """
        filepath = Path(target_path or self.voice_file)
        if not error_info:
            error_info = self.scan_syntax_errors(filepath)

        if not error_info:
            logger.info("No syntax error found to fix.")
            return True

        source = filepath.read_text(encoding="utf-8", errors="replace")
        
        # Save a backup of the corrupted file for diagnostics
        try:
            self.corrupt_file.write_text(source, encoding="utf-8")
        except Exception:
            pass

        lines = source.splitlines()
        lineno = error_info.get("lineno", 1)
        err_msg = error_info.get("msg", "").lower()
        err_text = error_info.get("text", "")

        fixed = False

        # --- HEURISTIC 1: Missing colon at end of block statements ---
        # e.g., 'def record_audio(self)' or 'if condition'
        if lineno <= len(lines):
            line_idx = lineno - 1
            line = lines[line_idx]
            stripped = line.strip()

            # Check if line starts with block statement keywords
            block_keywords = (
                "def ", "class ", "if ", "elif ", "else", "try", "except", "finally",
                "for ", "while ", "with ", "async def ", "async for ", "async with "
            )
            if any(stripped.startswith(kw) for kw in block_keywords) and not stripped.endswith(":"):
                # Append missing colon
                lines[line_idx] = line.rstrip() + ":"
                fixed = True

            # Check if the line before was missing a colon
            elif line_idx > 0:
                prev_line = lines[line_idx - 1]
                prev_stripped = prev_line.strip()
                if any(prev_stripped.startswith(kw) for kw in block_keywords) and not prev_stripped.endswith(":"):
                    lines[line_idx - 1] = prev_line.rstrip() + ":"
                    fixed = True

        # --- HEURISTIC 2: Unterminated string literal ---
        if not fixed and "unterminated string literal" in err_msg and lineno <= len(lines):
            line_idx = lineno - 1
            line = lines[line_idx]
            if line.count('"""') % 2 != 0:
                lines[line_idx] = line + '"""'
                fixed = True
            elif line.count("'''") % 2 != 0:
                lines[line_idx] = line + "'''"
                fixed = True
            elif line.count('"') % 2 != 0:
                lines[line_idx] = line + '"'
                fixed = True
            elif line.count("'") % 2 != 0:
                lines[line_idx] = line + "'"
                fixed = True

        # --- HEURISTIC 3: Unmatched or unclosed brackets/parentheses ---
        if not fixed and ("was never closed" in err_msg or "unmatched" in err_msg) and lineno <= len(lines):
            line_idx = lineno - 1
            line = lines[line_idx]
            # Add missing closing bracket
            if line.count("(") > line.count(")"):
                lines[line_idx] = line + ")" * (line.count("(") - line.count(")"))
                fixed = True
            elif line.count("[") > line.count("]"):
                lines[line_idx] = line + "]" * (line.count("[") - line.count("]"))
                fixed = True
            elif line.count("{") > line.count("}"):
                lines[line_idx] = line + "}" * (line.count("{") - line.count("}"))
                fixed = True

        # --- HEURISTIC 4: Stray invalid characters or broken inline statements ---
        if not fixed and lineno <= len(lines):
            line_idx = lineno - 1
            line = lines[line_idx]
            # Check if line is purely invalid characters or random typos
            if re.match(r"^\s*[^a-zA-Z0-9_#\s\'\"\(\)\[\]\{\}]+$", line):
                # Comment out the offending stray token line
                lines[line_idx] = "# [Auto-Healed] " + line
                fixed = True

        # Try saving the heuristic fix
        candidate_code = "\n".join(lines)
        if fixed:
            try:
                ast.parse(candidate_code)
                filepath.write_text(candidate_code, encoding="utf-8")
                logger.info(f"Heuristic syntax fix applied successfully at line {lineno}.")
                return True
            except (SyntaxError, IndentationError):
                pass  # Fall through to golden baseline

        # --- FALLBACK: Golden Baseline Restoration / Patch ---
        if self.golden_file.exists():
            try:
                golden_code = self.golden_file.read_text(encoding="utf-8")
                ast.parse(golden_code)
                filepath.write_text(golden_code, encoding="utf-8")
                logger.info(f"Restored {filepath.name} from golden baseline snapshot.")
                return True
            except Exception as e:
                logger.error(f"Golden baseline recovery failed: {e}")

        # If golden baseline is missing, write the candidate code anyway
        filepath.write_text(candidate_code, encoding="utf-8")
        return fixed

    # ==================== 3. TEST ====================

    def test_fix(self, target_path: Optional[Path] = None) -> bool:
        """
        Tests whether the target file compiles and parses without syntax errors.
        Returns True if test passes, False if errors remain.
        """
        err = self.scan_syntax_errors(target_path)
        return err is None

    # ==================== 4. RESTART VOICE SERVICE ====================

    def restart_voice_service(self) -> Any:
        """
        Reloads the voice_interface module and restarts the voice service instance.
        """
        logger.info("Restarting P.H.A.S.S Voice Service...")
        
        # 1. Reload module in sys.modules if already imported
        mod_name = "core.voice_interface"
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception as e:
                logger.warning(f"Could not reload module {mod_name}: {e}")

        # 2. Invoke restart_voice_service on the voice interface
        try:
            from core.voice_interface import restart_voice_service as _restart, get_voice_interface
            voice_inst = _restart()
            logger.info("Voice service restarted successfully.")
            return voice_inst
        except Exception as e:
            logger.error(f"Failed to restart voice service: {e}")
            try:
                from core.voice_interface import get_voice_interface
                return get_voice_interface()
            except Exception:
                return None

    # ==================== 5. STARTUP INTEGRATION ====================

    def update_golden_baseline(self, force: bool = False) -> bool:
        """
        Saves a known-good working snapshot of voice_interface.py as the golden baseline.
        """
        if not self.voice_file.exists():
            return False
        if not self.test_fix(self.voice_file):
            return False
        try:
            shutil.copy2(str(self.voice_file), str(self.golden_file))
            return True
        except Exception as e:
            logger.warning(f"Failed to update golden baseline: {e}")
            return False

    def ensure_voice_interface_healthy(self) -> Dict[str, Any]:
        """
        P.H.A.S.S Startup Self-Healing Routine:
        1. Scans core/voice_interface.py for syntax errors.
        2. If an error is found: writes fix, tests fix, and restarts voice service.
        3. If clean: updates golden baseline snapshot.
        """
        # Ensure golden baseline exists
        if not self.golden_file.exists():
            self.update_golden_baseline()

        err = self.scan_syntax_errors(self.voice_file)
        if not err:
            self.update_golden_baseline()
            return {
                "status": "HEALTHY",
                "message": "core/voice_interface.py syntax is clean and verified.",
                "repaired": False,
            }

        logger.warning(
            f"[Voice Guardian] Syntax error detected in {self.voice_file.name} "
            f"at line {err.get('lineno')}: {err.get('msg')}."
        )

        # Write the fix
        max_attempts = 3
        attempt = 0
        repaired = False

        while attempt < max_attempts and not self.test_fix(self.voice_file):
            attempt += 1
            current_err = self.scan_syntax_errors(self.voice_file)
            self.write_fix(self.voice_file, current_err)

        if self.test_fix(self.voice_file):
            repaired = True
            logger.info(f"[Voice Guardian] Syntax error repaired successfully in attempt {attempt}.")
        else:
            # Force restore from golden baseline
            if self.golden_file.exists():
                shutil.copy2(str(self.golden_file), str(self.voice_file))
                repaired = self.test_fix(self.voice_file)

        # Restart voice service
        voice_service = self.restart_voice_service()

        return {
            "status": "REPAIRED" if repaired else "FAILED",
            "message": (
                "Voice interface syntax repaired and voice service restarted."
                if repaired
                else "Failed to repair syntax error in core/voice_interface.py."
            ),
            "repaired": repaired,
            "error_detected": err,
            "voice_service_active": voice_service is not None,
        }


# Global singleton instance
voice_guardian = VoiceGuardian()


def ensure_voice_interface_healthy() -> Dict[str, Any]:
    """Module-level entry point to scan, fix, test, and restart voice service at startup."""
    if getattr(sys, "frozen", False):
        return {"status": "HEALTHY", "message": "Frozen standalone runtime.", "repaired": False}
    return voice_guardian.ensure_voice_interface_healthy()


def scan_voice_interface() -> Optional[Dict[str, Any]]:
    """Scan voice interface for syntax errors."""
    return voice_guardian.scan_syntax_errors()


def fix_and_restart_voice() -> Dict[str, Any]:
    """Fix syntax errors in voice interface, test, and restart."""
    return voice_guardian.ensure_voice_interface_healthy()
