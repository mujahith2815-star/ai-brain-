# Changelog

All notable changes to Orvix Sphere are documented in this file.

## [1.0.0 Zenith] - 2026-09-15

### Added
- **Standalone Executable Packaging**: PyInstaller single-file packaging (`build.py`) compiling `orvix_sphere.exe` with zero Python runtime dependency required on host systems.
- **Windows Auto-Start Background Daemon**: Task Scheduler service (`scripts/install_autostart.ps1` and `scripts/uninstall_autostart.ps1`) executing `orvix_sphere.exe --daemon` automatically on user logon.
- **Local Llama-3.2-1B-Instruct Engine**: Offline CPU inference integration (`core/local_llama_engine.py`) with thread-safe singleton pattern, zero-dependency CPU tensor loading, `/model`, `/warmup`, and `/benchmark` commands.
- **Windows Inno Setup Installer**: Graphical installer wizard (`installer/setup.iss`) producing `OrvixSphere_Setup_v1.0.0.exe` with desktop shortcut and optional auto-start setup.
- **Web Dashboard**: Modern FastAPI + Jinja2 + Tailwind CSS interface with live WebSockets, streaming chat, approval controls, and subsystem telemetry cards.
- **Rich Terminal UI**: Stylish ASCII banner, colored role-based message panels, structured telemetry tables, and code syntax highlighting.
- **SystemDoctor (`/doctor`)**: 10-point system health diagnostic scanner inspecting Python runtime, dependencies, SQLite, vector vaults, MCP, and disk space.
- **Proactive Autonomous Layer**: Cron task scheduler, watchdog filesystem monitors, edge-triggered condition watchers, and human-in-the-loop approval queue.
- **Model Context Protocol (MCP)**: Dynamic tool discovery and namespaced execution (`mcp__<server>__<tool>`) across SQLite, Filesystem, Fetch, and user servers.
- **Voice Intelligence Suite**: Whisper Speech-to-Text, pyttsx3 SAPI5 Text-to-Speech, wake word detection, and hands-free continuous loop mode.
- **Knowledge & RAG Memory**: SQLite persistent facts and lists, dense vector vault, and automatic inbox file watcher ingestion.
