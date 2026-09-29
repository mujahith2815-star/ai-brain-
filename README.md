# 🌐 Orvix Sphere Zenith v8.0.0
### Autonomous Cognitive AI, Dual-Brain Intelligence & Physical AI Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-cyan.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-emerald.svg)](https://fastapi.tiangolo.com/)
[![MCP Ready](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Google Gemini](https://img.shields.io/badge/AI-Gemini%202.0%20Flash-4285F4.svg)](https://aistudio.google.com/)

> 🚀 **Quick Access**:
> * **[QUICKSTART.md](QUICKSTART.md)** — 30-second setup and quick command reference.
> * **[ANTIGRAVITY_GUIDE.md](ANTIGRAVITY_GUIDE.md)** — Full guide for running & pairing in **Google Antigravity**.
> * **Windows 1-Click**: Double-click **`setup.bat`**, set your key in **`.env`**, then run **`run.bat`**!

---

## 📖 Table of Contents
1. [What is Orvix Sphere? (What For)](#-what-is-orvix-sphere-what-for)
2. [What Does It Use? Tech Stack & Tools (What To Use)](#-what-does-it-use-tech-stack--tools-what-to-use)
3. [How to Use It? (How To Use)](#-how-to-use-it-how-to-use)
   - [Method 1: Turnkey 1-Click Scripts (Recommended)](#method-1-turnkey-1-click-scripts-recommended)
   - [Method 2: Google Antigravity IDE](#method-2-google-antigravity-ide)
   - [Method 3: Standard Python Package Installation (`pip`)](#method-3-standard-python-package-installation-pip)
4. [Dual-Brain Cognitive Architecture](#-dual-brain-cognitive-architecture)
5. [Model Context Protocol (MCP) Integration](#-model-context-protocol-mcp-integration)
6. [Proactive Autonomous Sentinels](#-proactive-autonomous-sentinels)
7. [Environment Configuration (`.env`)](#-environment-configuration-env)
8. [CLI Commands Cheatsheet](#-cli-commands-cheatsheet)
9. [REST API Documentation](#-rest-api-documentation)
10. [Repository Structure](#-repository-structure)
11. [Testing & Quality Assurance](#-testing--quality-assurance)

---

## 🎯 What is Orvix Sphere? (What For)

**Orvix Sphere** is a production-grade autonomous cognitive assistant, physical AI simulator, and pair-programming operating system. It is designed to act as an always-on, intelligent sentinel that:

* **Reasons at Frontier Cloud Speeds**: Integrates **Google Gemini 2.0 Flash** for ultra-fast, high-context comprehension, coding, tool dispatch, and reasoning.
* **Never Drops Offline**: Features an intelligent **Dual-Brain Router** that automatically fails over to local models (Ollama Qwen2.5 / LLaMA) if the internet drops or rate limits are reached.
* **Acts Proactively Without Prompting**: Runs background cron sentinels that execute daily system health checks (8:00 AM) and automated 7-day rolling backups of all critical files (2:00 AM).
* **Interacts with Real-World Systems (MCP)**: Uses Anthropic's **Model Context Protocol (MCP)** to inspect local files, run SQLite queries, and fetch web endpoints safely.
* **Visualizes System Telemetry in 3D**: Comes with a real-time **Zenith WebGL 3D Dashboard** showing omnidirectional spherical movement, mental sandbox rollouts, battery telemetry, and error tracking.

---

## 🛠️ What Does It Use? Tech Stack & Tools (What To Use)

Orvix Sphere utilizes modern, lightweight, and resilient open-source libraries:

| Subsystem | Technologies Used | Why It Is Used |
| :--- | :--- | :--- |
| **Cognitive Brain (Cloud)** | `google-generativeai` | Connects to **Gemini 2.0 Flash** for 1M+ token context, high-speed coding, and reasoning. |
| **Cognitive Brain (Offline)** | `ollama`, PyTorch, Safetensors | Offline fallback (Qwen2.5-7B or LLaMA-3.2) ensuring total privacy and offline resilience. |
| **Tool Execution** | `mcp`, Node.js STDIO servers | Industry-standard **Model Context Protocol** providing isolated tools for Filesystem, SQLite, and Web Fetch. |
| **Web Server & API** | `fastapi`, `uvicorn`, `websockets` | High-throughput asynchronous ASGI web server powering the dashboard and real-time WebSocket telemetry. |
| **Dashboard UI** | `jinja2`, Three.js / WebGL, HTML5/CSS3 | Zero-bloat, responsive 3D dashboard with cyber-hud aesthetics, telemetry graphs, and chat interface. |
| **Proactive Scheduling** | `APScheduler`, `watchdog` | Non-blocking background scheduler for daily health audits, automated backups, and file system watchers. |
| **System Diagnostics** | `psutil`, `rich`, SQLite3 | Hardware monitoring (CPU, RAM, Disk), beautiful terminal formatting, and error event database (`logs/errors.db`). |
| **Configuration** | `python-dotenv`, `pydantic-settings` | Strongly-typed, 12-factor configuration via `.env` and YAML. |
| **Test Suite** | `pytest`, `pytest-asyncio` | Complete unit and integration test coverage across all core systems. |

---

## 🚀 How to Use It? (How To Use)

### Method 1: Turnkey 1-Click Scripts (Recommended)

#### On Windows:
1. **Setup**: Double-click **`setup.bat`**.
   * Automatically creates `.venv`, installs dependencies, registers console commands, and creates `.env`.
2. **Configure**: Open **`.env`** in any text editor and paste your free [Google AI Studio Gemini API Key](https://aistudio.google.com/):
   ```env
   GEMINI_API_KEY=your_actual_key_here
   ```
3. **Launch**:
   * **Web Dashboard**: Double-click **`run.bat`** (opens http://127.0.0.1:8000).
   * **Terminal Assistant**: Double-click **`run_cli.bat`**.

#### On Linux / macOS:
```bash
chmod +x *.sh
./setup.sh
# Edit your .env file with your GEMINI_API_KEY
./run.sh        # Starts Web Dashboard
./run_cli.sh    # Starts CLI Assistant
```

---

### Method 2: Google Antigravity IDE

Orvix Sphere is configured out-of-the-box for **Google Antigravity**:

1. In Antigravity, click **File > Open Folder...** and select `orvix_sphere`.
2. Select the virtual environment interpreter (`.\.venv\Scripts\python.exe` or `./.venv/bin/python`).
3. Set your `GEMINI_API_KEY` in `.env`.
4. In the Antigravity Terminal, run:
   ```powershell
   .\.venv\Scripts\python.exe -m web.launcher
   ```
   Or pair-program with the Antigravity agent directly (see **[ANTIGRAVITY_GUIDE.md](ANTIGRAVITY_GUIDE.md)**).

---

### Method 3: Standard Python Package Installation (`pip`)

You can install Orvix Sphere directly as a standard Python package with global console scripts:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
.\.venv\Scripts\activate        # Windows

# 2. Install editable package
pip install -e .

# 3. Copy configuration
cp .env.example .env

# 4. Run anywhere in your terminal
orvix-web     # Launches Uvicorn Web Dashboard & auto-opens browser
orvix         # Launches Interactive Conversational Terminal
```

---

## 🧠 Dual-Brain Cognitive Architecture

```text
               +------------------------------------------------+
               |                  USER DIRECTIVE                |
               +------------------------------------------------+
                                       |
                                       v
               +------------------------------------------------+
               |              COGNITIVE MODEL ROUTER            |
               |             (config/api_config.py)             |
               +------------------------------------------------+
                        |                              |
         [Online / Key Available]             [Offline / Rate Limit]
                        |                              |
                        v                              v
       +-------------------------------+   +-----------------------------+
       |   GOOGLE GEMINI 2.0 FLASH     |   |     LOCAL OLLAMA / QWEN     |
       |  - 1M+ Context Token Window   |   |  - Zero Network Footprint   |
       |  - High-Speed Cloud Reasoning |   |  - Total Privacy Fallback   |
       |  - Structured Tool Calling    |   |  - Deterministic Responses  |
       +-------------------------------+   +-----------------------------+
                        \                              /
                         \                            /
                          v                          v
               +------------------------------------------------+
               |            MODEL CONTEXT PROTOCOL (MCP)        |
               |        Filesystem | SQLite | Web Fetch API      |
               +------------------------------------------------+
```

---

## 🔌 Model Context Protocol (MCP) Integration

Orvix Sphere integrates standard Model Context Protocol STDIO servers located in `mcp/servers/`:

* **`filesystem` Server**: Read, write, list directories, and inspect file metadata within permitted workspace directories (`~/Documents` by default).
* **`sqlite` Server**: Safely query and inspect SQLite databases, schema definitions, and tables without arbitrary command injection.
* **`fetch` Server**: Extract readable markdown and text content from HTTP endpoints.

All MCP servers run isolated Node.js child processes with automatic reconnect and health heartbeats.

---

## 🛡️ Proactive Autonomous Sentinels

Orvix Sphere does not just wait for user commands — it monitors and maintains itself:

1. **Daily Health Check (`scripts/daily_health_check.py`)**:
   * Runs automatically at **8:00 AM** daily (configured via `proactive/triggers.json`).
   * Executes 10-point `SystemDoctor` diagnostic scan.
   * Audits disk space, CPU load, memory utilization, and active MCP servers.
   * Checks error occurrences logged in `logs/errors.db` in the past 24 hours.
   * Logs results to `logs/health_checks.log`.

2. **Automated Critical Data Backup (`scripts/backup_orvix.py`)**:
   * Runs automatically at **2:00 AM** daily.
   * Copies critical operational data:
     * `knowledge/` (RAG facts, knowledge triples)
     * `config/` (System & API configuration)
     * `proactive/triggers.json` (Autonomous triggers & scheduled jobs)
     * `logs/errors.db` (Historical error database)
   * Backs up to external storage (`W:/PHASS_MEMORY/backups/YYYYMMDD`) or falls back gracefully to `./backups/YYYYMMDD`.
   * Enforces strict **7-day retention policy** (automatically deletes archives older than 7 days).

---

## ⚙️ Environment Configuration (`.env`)

Copy `.env.example` to `.env`. All settings include sensible defaults:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(Required)* | Google Gemini API Key from [AI Studio](https://aistudio.google.com/) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Primary cloud model (`gemini-2.0-flash`, `gemini-1.5-flash`) |
| `MODEL_MODE` | `cloud_first` | Routing mode: `cloud_first`, `auto`, `cloud_only`, `local_only` |
| `FALLBACK_ENABLED` | `true` | Automatically fallback to local model when cloud fails |
| `RATE_LIMIT_RPM` | `14` | Safe rate limit buffer (free tier limit is 15 RPM) |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Endpoint for local Ollama instance |
| `LLAMA_MODEL` | `models/llama` | Path or name of local model weights |
| `ORVIX_WEB_HOST` | `127.0.0.1` | Web dashboard host binding |
| `ORVIX_WEB_PORT` | `8000` | Web dashboard port |

---

## ⌨️ CLI Commands Cheatsheet

When running `orvix` or `run_cli.bat`:

| Command | Action |
| :--- | :--- |
| `status` | Display robot health, battery %, internal temperature, and cognitive state |
| `/health` | Display the latest daily health check report and diagnostic status |
| `/health history` | Inspect past health check execution logs |
| `/errors` | Query recent system errors and warnings logged in `logs/errors.db` |
| `/errors clear` | Reset and purge historical error log entries |
| `/backup` | Trigger an immediate manual critical data backup |
| `/backup list` | List all historical backups and directory paths |
| `autogoal` | Evaluate environmental state and trigger autonomous goals |
| `kg` | Inspect semantic knowledge graph triples |
| `sim` | Run mental sandbox simulation rollouts |
| `tokens` | View token usage economics and context budgeting |
| `benchmark` | Run an automated 5-step model throughput benchmark |
| `help` | Print complete command listing |
| `exit` / `quit` | Cleanly terminate all background sentinels and shutdown |

---

## 📡 REST API Documentation

When the web server is running (`http://127.0.0.1:8000`):

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Live 3D WebGL Dashboard & Chat Interface |
| `/api/chat` | `POST` | Send natural language directive to the Dual-Brain cognitive engine |
| `/api/system/health` | `GET` | Real-time diagnostic health check (CPU, memory, disk, MCP, errors) |
| `/api/system/health/history`| `GET` | Historical health check audit records |
| `/api/system/errors` | `GET` | Recent system errors with severity filters (`ERROR`, `WARNING`) |
| `/api/backup/create` | `POST` | Trigger an immediate critical backup archive |
| `/api/backup/history` | `GET` | List all backups and disk utilization |
| `/api/mcp/status` | `GET` | Status of connected MCP servers and available tools |
| `/ws` | `WebSocket` | Real-time robot telemetry streaming (20 FPS) |

---

## 📁 Repository Structure

```text
orvix_sphere/
├── config/                 # Centralized configuration (API, LLaMA, system settings)
├── core/                   # Cognitive core, autonomous loop, goal manager
├── diagnostics/            # SystemDoctor, real-time monitors, hardware telemetry
├── mcp/                    # MCP configuration, client adapters, and STDIO servers
│   └── servers/            # Self-contained Node.js servers (sqlite, filesystem, fetch)
├── proactive/              # Proactive triggers (triggers.json) and cron scheduler
├── scripts/                # Automated backup and daily health check scripts
├── tools/                  # Gemini engine, MCP adapters, file & system tools
├── web/                    # FastAPI Zenith Web Dashboard and static assets
│   ├── static/             # CSS, WebGL scripts, icons
│   └── templates/          # Jinja2 dashboard templates
├── tests/                  # Automated pytest test suite
├── pyproject.toml          # Standard Python packaging & console script definitions
├── setup.py                # Backward-compatible package setup shim
├── requirements.txt        # Pinned runtime dependencies
├── .env.example            # Environment configuration template
├── setup.bat / setup.sh    # Turnkey 1-click installer scripts
├── run.bat / run.sh        # Turnkey 1-click web launcher scripts
├── run_cli.bat / .sh       # Turnkey 1-click CLI launcher scripts
├── QUICKSTART.md           # 30-second quickstart guide
└── ANTIGRAVITY_GUIDE.md    # Dedicated Google Antigravity developer guide
```

---

## 🧪 Testing & Quality Assurance

Run the complete test suite with zero configuration:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_web_api.py tests/test_gemini_engine.py tests/test_daily_health_check.py tests/test_backup.py -v
```

**Results**:
```text
38 passed, 0 failures (100% green)
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
