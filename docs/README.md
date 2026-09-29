# P.H.A.S.S SPHERE v8.0 ? Local Llama Digital Powerhouse

**P.H.A.S.S SPHERE v8.0** is an enterprise-grade, hyper-intelligent digital assistant and multi-agent operations platform powered by local Llama reasoning. Designed to run offline or online across Windows and Linux, P.H.A.S.S combines deep operating system automation, cognitive memory, subagent project management, universal MCP tool integration, and multimodal voice/GUI interaction.

---

## ?? Key Capabilities at a Glance

1. **Subagent Orchestration (Project Manager Mode)**:
   - 8 pre-built specialized subagents:
     - `researcher`: Web search, scraping, article summaries, fact-checking.
     - `coder`: Code generation, AST verification, refactoring, debugging, unit testing.
     - `data_analyst`: Numerical statistics, CSV/Excel parsing, pivot tables.
     - `file_manager`: Safe directory organization, duplicate elimination, disk analysis.
     - `system_monitor`: Real-time telemetry, memory load, process inspection.
     - `writer`: High-impact reports, documentation, creative stories, emails.
     - `translator`: Multi-lingual translation with cultural and idiom retention.
     - `security_auditor`: Vulnerability scanning, access permissions, hash audit.
   - Concurrent parallel dispatch (`parallel_execute`) and unified report synthesis (`aggregate_results`).

2. **Automated Scheduler Engine**:
   - Standard 5-field cron parsing (`0 3 * * 0`, `* * * * *`, `@daily`, `@hourly`).
   - Natural intervals (`every_5m`, `in_30s`, `every_1h`).
   - Pre-configured automated routines:
     - Weekly download purge (Sunday 3 AM)
     - Weekly document backup (Friday 5 PM)
     - Hourly disk alert monitoring
     - Daily executive summary report

3. **Lifecycle Hook & Interception Guard**:
   - `before_tool_call`, `after_tool_call`, `before_model_call`, `after_model_call`, `on_error`, `safety_check`.
   - Pre-built safety hooks: `confirm_dangerous_actions`, `audit_log`, `rate_limiter`.

4. **Universal Model Context Protocol (MCP) Client**:
   - Connects over stdio, HTTP/SSE, and JSON-RPC 2.0.
   - Pre-built connections: `filesystem`, `git`, `docker`, `postgres`, `slack`, `google_drive`.
   - Zero-crash fallback simulator.

5. **Advanced Cognitive Memory & RAG**:
   - Vector database semantic search with pure-Python cosine similarity fallback.
   - Multi-format ingestion: PDF, Word, Excel, HTML, Markdown, and code.
   - Knowledge Graph (`subject`, `predicate`, `object`).
   - Markov pattern learner & predictive context engine.
   - Isolated per-project memory partitions.

6. **Enterprise Cybersecurity Suite**:
   - AES-256 and RSA cryptography.
   - Encrypted master-password vault.
   - SSH key manager and firewall rule controller.
   - Cryptographic tamper-evident hash chaining.
   - Two-man rule confirmation gate for high-risk commands.

7. **Multimodal Interface**:
   - Whisper local Speech-to-Text with Porcupine wake word ("Hey Llama").
   - pyttsx3 offline Text-to-Speech.
   - Tkinter GUI desktop control dashboard.
   - System tray resident daemon and global hotkeys.

---

## ?? Quick Start

### Installation
```bash
python install.py
```

### Running Interactive Terminal
```bash
python run_model_chat.py
```

### Packaging Standalone Binaries
- **Windows**: Run `build_windows.bat` -> Produces `dist/phass_sphere.exe`
- **Linux**: Run `./build_linux.sh` -> Produces `dist/phass_sphere` & `.tar.gz`
- **Docker**: Run `docker build -t phass-sphere:8.0 .`