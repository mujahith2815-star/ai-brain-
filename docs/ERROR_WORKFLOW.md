# Orvix Sphere — Human-in-the-Loop Error & Repair Workflow (v1.4.2)

## Overview

Orvix Sphere does **not** perform autonomous or self-modifying code repairs on itself. Self-patching code is prone to hallucinated logic, broken dependencies, and silent corruption. Instead, Orvix Sphere pairs with **Antigravity** in a deterministic **Human-in-the-Loop Repair Architecture**:

1. **Orvix Observes and Logs**: All tool failures, unhandled exceptions, and runtime errors are automatically deduplicated and logged to SQLite at `logs/errors.db`.
2. **Human Reviews**: The operator inspects recent or recurring errors via `/errors` or `/errors top`.
3. **Copy-Paste Bug Report**: The operator types `/errors <id>` to retrieve an exact, reproduction-ready bug report with source code locations, parameter context, and stack traces.
4. **Antigravity Repairs**: The operator pastes the report into Antigravity with the prompt: *"Fix this bug and add a test."*
5. **Antigravity Tests & Verifies**: Antigravity applies the targeted patch, writes regression tests, and runs the test suite.
6. **Resolved**: The operator resumes or restarts Orvix; the error count stops incrementing.

---

## The 7-Step Workflow

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  1. Error in    │  ───> │  2. Inspect     │  ───> │  3. Copy Report │
│     Orvix       │       │     /errors     │       │     /errors <id>│
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  6. Resume      │  <─── │  5. Test &      │  <─── │  4. Paste into  │
│     Orvix       │       │     Verify      │       │     Antigravity │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### Step 1: An Error Occurs
When a tool execution fails or an exception occurs during runtime:
- Orvix catches the failure and logs it to `logs/errors.db`.
- The observation sent to the reasoning engine notes:
  `[This error logged as ID 42. Use /errors 42 to see full report.]`
- Identical errors are deduplicated via SHA-256 hash `(error_type + error_message)`, incrementing `count` and updating `last_seen` without spamming logs.

### Step 2: Operator Inspects Digest
In the Orvix terminal interface:
```bash
Operator >> /errors
```
Output:
```text
📋 Recent Errors in Orvix Sphere:
  ID    Count   Category        Error Type           Message                          Last Seen
  ----- ------- --------------- -------------------- -------------------------------- -------------------
  #1    3       TOOL_FAILURE    ToolExecutionError   File does not exist: notes.txt   2026-09-18 11:30:00
  #2    1       UNCAUGHT        KeyError             'temperature'                    2026-09-18 11:32:15
```

To see the most frequent recurring errors across the last 30 days:
```bash
Operator >> /errors top
```

### Step 3: Generate Bug Report
Retrieve the copy-paste-ready report for the specific error:
```bash
Operator >> /errors 1
```

Output:
```text
┌─────────────────────────────────────────────────────────────┐
│ BUG REPORT — ready to paste into Antigravity                │
├─────────────────────────────────────────────────────────────┤
│ ERROR ID:    1                                              │
│ TIMESTAMP:   2026-09-18 11:30:00                            │
│ CATEGORY:    TOOL_FAILURE                                   │
│ SOURCE:      core/llama_tool_agent.py:_execute_tool_sync    │
│ COUNT:       3                                              │
│                                                             │
│ ERROR: File does not exist: notes.txt                       │
│                                                             │
│ CONTEXT:                                                    │
│   tool: file_reader                                         │
│   args: {"path": "notes.txt"}                               │
│   recent_tools: ['file_reader']                             │
│                                                             │
│ TRACEBACK:                                                  │
│   File "tools/file_ops.py", line 45, in read_file           │
│   FileNotFoundError: [Errno 2] No such file or directory    │
│                                                             │
│ REPRODUCE:                                                  │
│   Run: python run_model_chat.py                             │
│   Command: Read notes.txt                                   │
│                                                             │
│ SUGGESTED ACTION:                                           │
│   Paste this entire report into Antigravity.                │
│   Ask: "Fix this bug and add a test."                       │
└─────────────────────────────────────────────────────────────┘
```

### Step 4: Paste into Antigravity
Open Antigravity paired session and paste the block:
> "Fix this bug and add a test:
> [Paste box from /errors <id>]"

### Step 5: Antigravity Applies Fix & Regression Test
Antigravity:
1. Inspects the source file indicated in `SOURCE`.
2. Recreates the error condition using parameters in `CONTEXT`.
3. Implements the minimal, robust fix.
4. Adds a unit test in `tests/`.
5. Executes `pytest` across the full test suite.

### Step 6: Export Full Error Digest (Optional)
If multiple errors need to be reviewed or documented in a PR:
```bash
Operator >> /errors export
```
Exports all recent and top recurring errors to `logs/error_digest.md`.

### Step 7: Clear Stale Errors
To prune old resolved errors older than 30 days:
```bash
Operator >> /errors clear
```

---

## Available Slash Commands

| Command | Purpose |
| :--- | :--- |
| `/errors` | Show table of 10 most recent errors. |
| `/errors <id>` | Print copy-paste-ready bug report for error `<id>`. |
| `/errors top` | Show top 10 recurring errors sorted by occurrence count. |
| `/errors export` | Export markdown digest to `logs/error_digest.md`. |
| `/errors clear` | Delete error records older than 30 days. |

---

## Programmatic Error Tools

LLM agents and automated scripts can also interact with the error logger via built-in tools:
- `log_error(category, error_type, error_message, source_file, traceback, context)`: Record an error.
- `get_errors(limit, category)`: Query recent error records.
- `get_error_stats()`: Retrieve total error counts and top 5 recurring categories.
