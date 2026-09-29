# 🚀 Orvix Sphere — Quickstart Guide

Welcome to **Orvix Sphere** — an autonomous cognitive intelligence & physical AI framework featuring Google Gemini cloud reasoning, local offline fallbacks, proactive background health monitoring, Model Context Protocol (MCP) integrations, and a live 3D WebGL dashboard.

---

## ⚡ 30-Second Turnkey Setup

### On Windows
1. Double-click **`setup.bat`** (or open PowerShell/CMD in the project root and run `.\setup.bat`).
   * This automatically provisions the `.venv`, installs all package dependencies, registers `orvix` / `orvix-web` console commands, and creates `.env`.
2. Open **`.env`** in any text editor and paste your free Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
   *(Get your free key at [Google AI Studio](https://aistudio.google.com/))*
3. Launch:
   * **Web Dashboard**: Double-click **`run.bat`** (opens http://127.0.0.1:8000 in your browser).
   * **Terminal Assistant**: Double-click **`run_cli.bat`** (starts the interactive conversational terminal).

---

### On Linux / macOS
1. Make scripts executable and run setup:
   ```bash
   chmod +x *.sh
   ./setup.sh
   ```
2. Edit `.env` and set your `GEMINI_API_KEY`:
   ```bash
   nano .env
   ```
3. Launch:
   * **Web Dashboard**: `./run.sh`
   * **Terminal Assistant**: `./run_cli.sh`

---

## 📦 Python Package Installation (`pip`)

You can also install and run Orvix Sphere directly as a standard Python package:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux / macOS
# or on Windows:
.\.venv\Scripts\activate

# 2. Install Orvix Sphere in editable mode
pip install -e .

# 3. Copy configuration template
cp .env.example .env

# 4. Run via registered console commands
orvix-web     # Launches the web dashboard
orvix         # Launches the interactive terminal
```

---

## 🛠️ Essential Interactive Commands

When using the interactive terminal (`run_cli.bat` or `orvix`):

| Command | Action |
| :--- | :--- |
| `status` | Shows robot status, battery, temperature, cognitive state |
| `/health` | Shows latest health check diagnostics and error summary |
| `/health history` | Shows recent health check historical logs |
| `/errors` | Shows recent system errors logged in `logs/errors.db` |
| `/errors clear` | Clears system error log database |
| `/backup` | Creates an immediate critical data backup |
| `/backup list` | Lists all historical backups and storage locations |
| `autogoal` | Evaluates and triggers proactive autonomous goals |
| `kg` | Inspects semantic knowledge graph triples |
| `exit` / `quit` | Gracefully shuts down autonomous engines |

---

## 🧪 Running the Test Suite

Validate all core components with a single command:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_web_api.py tests/test_gemini_engine.py tests/test_daily_health_check.py tests/test_backup.py -q
```
All 38 core tests should pass with green status.

---

## 🌐 Web Dashboard Highlights (http://127.0.0.1:8000)

* **Hybrid AI Engine**: Real-time Gemini 2.0 Flash cloud reasoning with automatic offline fallback.
* **MCP Status**: Live monitoring of Model Context Protocol STDIO servers (`filesystem`, `sqlite`, `fetch`).
* **Live Telemetry**: Spherical omni-directional motion telemetry, mental sandbox, and battery telemetry.
* **Proactive Triggers**: Automated daily health check (8:00 AM) and critical data backup (2:00 AM).
