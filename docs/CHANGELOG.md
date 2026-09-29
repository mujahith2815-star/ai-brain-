# Changelog ? P.H.A.S.S SPHERE

All notable changes to the P.H.A.S.S SPHERE AI assistant are documented in this file.

## [8.0.0] - 2026-09-05 ? "Crazy Cool Good" Universal Powerhouse Release

### Added
- **Subagent Project Manager (`core/subagent_orchestrator.py`)**:
  - 8 pre-built specialized subagents (`researcher`, `coder`, `data_analyst`, `file_manager`, `system_monitor`, `writer`, `translator`, `security_auditor`).
  - Concurrent thread-pool dispatch (`parallel_execute`) and unified report aggregator (`aggregate_results`).
- **Cron Scheduler & Automation Engine (`core/scheduler_engine.py`)**:
  - Full 5-part cron syntax parser (`0 3 * * 0`, `0 17 * * 5`, `* * * * *`).
  - Pre-configured routine schedules: clean downloads, backup documents, disk check alert, daily executive report.
  - Job pause and resume state controls.
- **Interception & Safety Guard Engine (`core/hook_engine.py`)**:
  - Lifecycle interception points (`before_tool_call`, `after_tool_call`, `before_model_call`, `after_model_call`, `on_error`, `safety_check`).
  - Pre-built guardrails: `confirm_dangerous_actions`, cryptographic `audit_log`, and `rate_limiter`.
- **Universal Model Context Protocol Client (`core/mcp_client.py`)**:
  - Stdio and JSON-RPC 2.0 client.
  - Pre-built templates for `filesystem`, `git`, `docker`, `postgres`, `slack`, and `google_drive` with zero-crash fallbacks.
- **Deep Cognitive Memory & RAG (`core/memory_master.py`)**:
  - Pure-Python cosine vector search over document chunks.
  - Multi-format ingestion (PDF, Word, Excel, HTML, Markdown).
  - Semantic Knowledge Graph (`subject`, `predicate`, `object`).
  - Markov action pattern learner and predictor.
  - Isolated per-project memory environments.
- **Proactive Intelligence Sentinel (`core/proactive_engine.py`)**:
  - Temporal context prediction and recommendation engine.
  - Telemetry alert system for disk fill and unhandled errors.
  - Contextual reminder scheduler and autonomous workflow runners.
- **Multimodal Human-AI Interface (`core/interface_master.py`)**:
  - Voice input/output coordination with Whisper STT and pyttsx3 TTS.
  - Interactive Tkinter desktop control GUI.
  - System tray resident status daemon and global hotkeys (`Ctrl+Shift+L`).
- **Web Master Tool Suite (`tools/web_master.py`)**:
  - Headless browser automation, web scraper, form filler, auto login, YouTube controller, download manager, and RSS reader.
- **Document Master Tool Suite (`tools/document_master.py`)**:
  - Manipulators for PDF, Excel, Word, PowerPoint, images, video metadata, and archives.
- **Security Master Tool Suite (`tools/security_master.py`)**:
  - AES-256/RSA cryptography, encrypted password vault, SSH manager, firewall manager, threat detection, and confirmation gate tokens.
- **Fun & Entertainment Suite (`tools/fun_tools.py`)**:
  - Procedural vector SVG image generator, multi-genre story generator, joke generator, trivia game, music player, and game controller.
- **Packaging & Build System**:
  - `build_windows.bat` (PyInstaller Windows PE binary `dist/phass_sphere.exe`).
  - `build_linux.sh` (PyInstaller Linux ELF binary and `.tar.gz`).
  - `Dockerfile` (multi-stage minimal runtime container).
- **Documentation**:
  - Complete suite: `docs/README.md`, `docs/USER_GUIDE.md`, `docs/DEVELOPER_GUIDE.md`, `docs/API_REFERENCE.md`, `docs/CHANGELOG.md`.

### Changed
- Expanded `tool_registry` from 174 tools to 206 registered tools.
- Upgraded `core/llama_tool_agent.py` to route subagent commands before file operations.
- Upgraded `core/hook_engine.py` to support variable positional and keyword arguments.