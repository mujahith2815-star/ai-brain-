# 🤖 Google Antigravity Developer Guide for Orvix Sphere

This guide explains how to open, develop, test, and run **Orvix Sphere** inside **Google Antigravity**.

---

## 1. Opening the Project in Antigravity

1. Launch **Google Antigravity**.
2. Select **File > Open Folder...** and choose the `orvix_sphere` directory.
3. In Antigravity's bottom status bar (or command palette `Ctrl+Shift+P` > `Python: Select Interpreter`), select the local virtual environment:
   * Windows: `.\.venv\Scripts\python.exe`
   * Linux / macOS: `./.venv/bin/python`

> [!TIP]
> If `.venv` doesn't exist yet, simply run `setup.bat` (Windows) or `./setup.sh` (Linux/macOS), or ask the Antigravity agent:
> *"Please set up the virtual environment and install dependencies."*

---

## 2. Configuring Environment & API Keys

Orvix Sphere uses a `.env` file for runtime credentials and settings.

1. Ensure `.env` is created from the template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in Antigravity and provide your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.0-flash
   MODEL_MODE=cloud_first
   ```
   * Free Gemini API keys can be obtained instantly at [Google AI Studio](https://aistudio.google.com/).
   * With `MODEL_MODE=cloud_first`, Orvix uses Gemini 2.0 Flash for ultra-fast, intelligent reasoning with zero local GPU requirements, and gracefully degrades to local fallbacks if offline.

---

## 3. Package Structure & CLI Tools

Orvix Sphere is a fully packaged Python library compliant with `pyproject.toml` and `setup.py`.

```text
orvix_sphere/
├── config/              # Centralized configuration (API, LLaMA, system settings)
├── core/                # Cognitive Core, autonomous loops, unified orchestrator
├── diagnostics/         # SystemDoctor, realtime monitors, hardware telemetry
├── mcp/                 # Model Context Protocol clients, config, and STDIO servers
├── proactive/           # Proactive triggers (triggers.json, cron scheduler)
├── scripts/             # Backup (backup_orvix.py), health checks (daily_health_check.py)
├── tools/               # Gemini AI engine, MCP adapters, system tools
├── web/                 # FastAPI Zenith Web Dashboard & static assets
├── tests/               # Comprehensive automated test suite
├── pyproject.toml       # Package metadata and console script definitions
├── setup.py             # Backward-compatible setup file
├── .env.example         # Documented environment template
├── setup.bat / .sh      # Turnkey 1-click installation scripts
└── run.bat / .sh        # Turnkey 1-click execution scripts
```

Once installed via `pip install -e .`, two console scripts are available globally in the venv:
* `orvix` — Runs the interactive conversational terminal (`phass_cli:main`).
* `orvix-web` — Launches the Uvicorn web server and opens the browser (`web.launcher:main`).

---

## 4. Running the Web Dashboard

Inside Antigravity's integrated terminal or using a terminal command:

```powershell
# Launch Web Dashboard
.\.venv\Scripts\python.exe -m web.launcher
```

Or execute `run.bat`.

The dashboard will be available at:
👉 **`http://127.0.0.1:8000`**

### REST API Endpoints:
* `GET /api/system/health` — Full diagnostic health status (CPU, memory, disk, MCP, errors)
* `GET /api/system/health/history` — Historical health check log entries
* `GET /api/system/errors` — Recent error log query with severity filters
* `POST /api/backup/create` — Trigger critical data backup
* `GET /api/backup/history` — Inspect backup archives
* `GET /api/mcp/status` — Model Context Protocol servers health & connected tools
* `POST /api/chat` — Send query to the hybrid cognitive AI engine

---

## 5. Running the Interactive Terminal Assistant

In Antigravity's terminal:

```powershell
.\.venv\Scripts\python.exe phass_cli.py
```

Try typing:
* `status`
* `/health`
* `/backup`
* `/errors`
* `What tasks can you perform today?`

---

## 6. Running Tests in Antigravity

Antigravity can automatically discover and run pytest tests. To run them manually in the terminal:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_web_api.py tests/test_gemini_engine.py tests/test_daily_health_check.py tests/test_backup.py -v
```

All 38 core tests verify:
1. **Web API**: Dashboard rendering, chat endpoint, MCP status, health endpoints, backup API.
2. **Gemini Engine**: Model routing, fallback retry logic, API error recovery, token estimation.
3. **Daily Health Check**: SystemDoctor execution, disk space, proactive task validation, error count tracking.
4. **Backup System**: Daily critical folder backup, 7-day retention cleanup, missing drive fallback.

---

## 7. Pair Programming with Antigravity Agent

When working with the Antigravity AI Agent on this repository, you can ask it tasks such as:

* *"Add a new MCP server for GitHub integration to `config/mcp_servers.json`"*
* *"Add a new proactive trigger to `proactive/triggers.json`"*
* *"Run the test suite and verify everything passes"*
* *"Check system diagnostics and error logs using `/health`"*

The codebase is modular, clean, and pre-configured for full agentic pair programming!
