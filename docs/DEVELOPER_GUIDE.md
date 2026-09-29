# Orvix Sphere Developer Guide

## Architecture Overview
Orvix Sphere follows a clean modular layout:
- `core/`: Primary reasoning agent (`llama_tool_agent.py`), secondary brain (`secondary_brain.py`), and platform abstractions.
- `knowledge/`: SQLite persistent store (`sqlite_store.py`) and vector vault.
- `voice/`: STT (`speech_to_text.py`), TTS (`text_to_speech.py`), wake word (`wake_word.py`).
- `mcp/`: Model Context Protocol JSON-RPC client, manager, and adapter.
- `proactive/`: TaskScheduler, FileSystemWatcher, ConditionWatcher, SafetyGuard, AutonomousAgent.
- `web/`: FastAPI app, Jinja2 templates, static assets, WebSocket handler.
- `cli/`: Rich console formatting and daemon handler.

## Adding Custom Tools
1. Define tool function in `tools/builtin_tools.py` with `@tool_registry.register(...)`.
2. Specify input parameter schemas for JSON validation.
3. Add unit test in `tests/`.

## Running Test Suites
```powershell
pytest tests/test_web_api.py -v
pytest tests/test_diagnostics.py -v
pytest tests/test_proactive_layer.py -v
```
