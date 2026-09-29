from pathlib import Path

walkthrough_file = Path(r"C:\Users\ph50\.gemini\antigravity\brain\1593a281-18e0-466e-ba00-222cb7d64e02\walkthrough.md")
content = walkthrough_file.read_text(encoding="utf-8")

autonomic_section = """
---

# Autonomic Error Recovery Circuit Walkthrough

The Autonomic Error Recovery Circuit transforms P.H.A.S.S from requiring manual bug fixes into a fully autonomous, closed-loop self-healing system. It automatically captures runtime exceptions, categorizes them, retrieves verified fixes from a local known error database or synthesizes them using heuristic/LLM rules, validates candidate patches in an isolated sandbox, hot-deploys them with non-blocking service restarts, and enforces an automatic 60-second rollback guard.

---

## 1. Core Recovery Circuit Architecture

### A. The Error Analyzer ([`core/error_analyzer.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/error_analyzer.py))
- **Continuous Log Watcher**: Scans execution logs and raw tracebacks from `checkpoints/execution_log.json` and stderr streams.
- **5-Domain Fault Classifier**:
  1. `ImportError` / `ModuleNotFoundError` -> `IMPORT_MODULE_FAULT`
  2. `SyntaxError` / `IndentationError` -> `SYNTAX_PARSER_FAULT`
  3. `AttributeError` / `NameError` -> `VARIABLE_OR_ATTRIBUTE_FAULT`
  4. `TimeoutError` / `ConnectionError` -> `NETWORK_OR_TIMEOUT_FAULT`
  5. `FileNotFoundError` / `PermissionError` -> `FILESYSTEM_PERMISSION_FAULT`
- **Levenshtein Similarity Engine**: Uses pure-Python edit distance matching against [`checkpoints/known_errors.json`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/checkpoints/known_errors.json). Patterns with similarity $\ge 0.85$ immediately trigger cached solutions for sub-second repair.

### B. The Fix Generator ([`core/fix_generator.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/fix_generator.py))
- **Context Extraction**: Accurately extracts file path, offending line number, and code context.
- **Dual Fix Synthesis**:
  - *Path 1*: Cached known fixes (e.g. `import re`, `import json`, missing dependencies).
  - *Path 2*: Deterministic heuristic rules (missing imports cleanly placed after docstrings and `from __future__`, missing colons, unterminated string literals) with local LLM prompt construction for complex faults.
- **Strict 70% Confidence Safety Valve**:
  - Confidence $\ge 70\%$: Marks `status = "READY_FOR_SANDBOX"` and proceeds to validation.
  - Confidence $< 70\%$: Immediately halts automated modification, marks `status = "NEEDS_USER_REVIEW"`, flags `escalate_to_user = True`, and alerts the user.

### C. The Sandbox Validator ([`core/fix_validator.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/fix_validator.py))
- **Isolation Mode**: Replicates candidate fix into `sandbox/` folder without touching the live file.
- **Two-Tier Gating**:
  1. AST & `py_compile` compilation check.
  2. Associated unit test suite execution via `pytest`.
- Corrupt or broken fixes fail validation immediately, leaving live codebase files untouched.

### D. The Rollback & Deploy Manager ([`core/rollback_manager.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/rollback_manager.py))
- **Pre-Fix Backup**: Archives target file to `checkpoints/backups/[filename]_[timestamp].bak` prior to disk write.
- **Hot Deployment**: Writes validated code to live file and reloads module in `sys.modules` / restarts affected background services (e.g. `VoiceGuardian`).
- **60-Second Crash Watcher**: If an unhandled exception occurs within 60 seconds of deployment, instantly restores the `.bak` file and alerts:
  `"Sir, my attempt to fix [error] failed. I've rolled back to the previous version."`
- **Immunity Metrics**: Persists `errors_fixed_today`, `pending_review`, and `rollbacks` in [`checkpoints/immunity_metrics.json`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/checkpoints/immunity_metrics.json).
- **Weekly Backup Retention**: Automatically purges `.bak` files older than 7 days.

### E. Circuit Coordinator ([`core/autonomic_circuit.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/autonomic_circuit.py))
- Exposes `heal_runtime_error(...)` which executes the full closed-loop pipeline from error detection to verified deployment.

---

## 2. System Integrations

1. **Proactive Monitor ([`core/proactive_monitor.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/proactive_monitor.py))**:
   - Added `alert_autonomic_fix(module_name)`:
     `"[P.H.A.S.S Interrupts] Sir, I detected an error in my own {module_name} module. I have generated a fix and am testing it in the sandbox."`

2. **Autopilot Mode ([`core/autopilot_mode.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/core/autopilot_mode.py))**:
   - Added `run_weekly_error_audit()`: purges `.bak` files older than 7 days and compacts duplicate patterns in `known_errors.json`.

3. **Holographic UI Immunity Panel ([`ui/main_window.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/ui/main_window.py))**:
   - Added **"🛡 Immunity"** tab to the Holographic Tabview.
   - Displays 3 live metric cards: **Errors Fixed Today**, **Pending Review (<70%)**, **Rollbacks (60s Guard)**.
   - Displays live stream of recovery actions with "🔄 Refresh Metrics" and "🧹 Run Weekly Audit" buttons.

4. **Tools Integration ([`tools/web_search.py`](file:///C:/Users/ph50/.gemini/antigravity/scratch/orvix_sphere/tools/web_search.py))**:
   - Added regex query sanitization using `re.sub()`. Deleting `import re` reliably triggers a `NameError` for autonomous recovery testing.

---

## 3. Verification & Test Results

### A. Dedicated Test Suite (`tests/test_self_healing.py`):
Ran `pytest tests/test_self_healing.py -v`:
```text
tests/test_self_healing.py::test_error_capture PASSED                    [ 16%]
tests/test_self_healing.py::test_fix_generation PASSED                   [ 33%]
tests/test_self_healing.py::test_sandbox_validation PASSED               [ 50%]
tests/test_self_healing.py::test_rollback_recovery PASSED                [ 66%]
tests/test_self_healing.py::test_e2e_self_healing_acid_test PASSED       [ 83%]
tests/test_self_healing.py::test_proactive_alert_and_autopilot_audit PASSED [100%]

============================== 6 passed in 3.17s ==============================
```

### B. Full Regression Suite (25/25 Passing):
Ran `pytest tests/test_self_healing.py tests/test_proactive_yes_no.py tests/test_voice_guardian.py tests/test_conversational_balance.py tests/test_ambient_intelligence.py -v`:
```text
tests/test_self_healing.py::test_error_capture PASSED                    [  4%]
tests/test_self_healing.py::test_fix_generation PASSED                   [  8%]
tests/test_self_healing.py::test_sandbox_validation PASSED               [ 12%]
tests/test_self_healing.py::test_rollback_recovery PASSED                [ 16%]
tests/test_self_healing.py::test_e2e_self_healing_acid_test PASSED       [ 20%]
tests/test_self_healing.py::test_proactive_alert_and_autopilot_audit PASSED [ 24%]
tests/test_proactive_yes_no.py::test_proactive_confirm_flow PASSED       [ 28%]
tests/test_proactive_yes_no.py::test_proactive_decline_flow PASSED       [ 32%]
tests/test_proactive_yes_no.py::test_proactive_affirmation_and_decline_variations PASSED [ 36%]
tests/test_proactive_yes_no.py::test_proactive_monitor_5_minute_cooldown PASSED [ 40%]
tests/test_voice_guardian.py::test_voice_guardian_clean_scan PASSED      [ 44%]
tests/test_voice_guardian.py::test_voice_guardian_detects_missing_colon_syntax_error PASSED [ 48%]
tests/test_voice_guardian.py::test_voice_guardian_fixes_and_tests_missing_colon PASSED [ 52%]
tests/test_voice_guardian.py::test_voice_guardian_fixes_unterminated_string_literal PASSED [ 56%]
tests/test_voice_guardian.py::test_voice_guardian_fallback_to_golden_on_severe_corruption PASSED [ 60%]
tests/test_voice_guardian.py::test_voice_guardian_restart_voice_service PASSED [ 64%]
tests/test_voice_guardian.py::test_voice_guardian_startup_self_heal_routine PASSED [ 68%]
tests/test_conversational_balance.py::test_greeting_routes_to_chat PASSED [ 72%]
tests/test_conversational_balance.py::test_build_programme_routes_to_project PASSED [ 76%]
tests/test_conversational_balance.py::test_project_creation_with_named_project PASSED [ 80%]
tests/test_ambient_intelligence.py::test_service_installer_configurations PASSED [ 84%]
tests/test_ambient_intelligence.py::test_wake_word_phrases_and_tray_indicator PASSED [ 88%]
tests/test_ambient_intelligence.py::test_ambient_vision_compilation_error_detection PASSED [ 92%]
tests/test_ambient_intelligence.py::test_autopilot_autonomous_mode PASSED [ 96%]
tests/test_ambient_intelligence.py::test_ambient_screen_nlp_query PASSED [100%]

============================= 25 passed in 12.01s =============================
```

### C. Live Acid Test Execution (`scratch/acid_test_verification.py`):
```text
=== ACID TEST: AUTONOMIC ERROR RECOVERY CIRCUIT ===
Target Module: tools/web_search.py

[Step 1] Intentionally deleting 'import re' from tools/web_search.py...
[Step 2] Executing search query 'arduino decoupling capacitor'...
-> CAUGHT RUNTIME ERROR: NameError: name 're' is not defined

[Step 3] Engaging Autonomic Circuit closed-loop self-repair...
-> Diagnosis: NameError (VARIABLE_OR_ATTRIBUTE_FAULT)
-> Similarity Match: Insert missing import re at module top
-> Generated Fix Confidence: 98.0%
-> Sandbox Syntax OK: True
-> Pre-Fix Backup: web_search.py_20260908_210559.bak
-> Hot Deployment Success: True
-> Circuit Message: Autonomous self-healing completed for web_search.py: Fix deployed with backup web_search.py_20260908_210559.bak.

[Step 4] Re-triggering search query through restored module...
-> Search Status: SUCCESS
-> Snippet: On Arduino boards (such as the Uno with ATmega328P), a 0.1 uF (100 nF) ceramic capacitor is connected as a decoupling ca...

[SUCCESS] ACID TEST COMPLETE: System autonomously detected, validated, deployed, and verified fix!
```
"""

walkthrough_file.write_text(content + autonomic_section, encoding="utf-8")
print("Appended autonomic section to walkthrough.md successfully.")
