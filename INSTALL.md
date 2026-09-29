# P.H.A.S.S SPHERE ZENITH v8.0 — INSTALLATION & DEPLOYMENT GUIDE

P.H.A.S.S Sphere Zenith is an autonomous, self-learning, cross-platform AI assistant and multi-domain digital operations center powered by local Llama models.

---

## ⚡ 1-Minute Quickstart

### On Linux or macOS
```bash
bash get_llama.sh
```

### On Windows (PowerShell)
```powershell
.\get_llama.ps1
```

Or execute the universal installer directly:
```bash
python auto_install.py
```

---

## 🖥️ System Requirements & Hardware Tiers

The system automatically detects your hardware architecture and configures the optimal Llama parameter tier:

| Tier | System RAM | GPU / VRAM | Recommended Model | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Ultra-Compact** | 4GB – 8GB | None (CPU) | `llama3.2:1b` | Embedded devices, ultra-low power, edge |
| **Lightweight** | 8GB – 16GB | None / 4GB VRAM | `llama3.2:3b` | Laptops, consumer desktops, low latency |
| **Sweet Spot (Recommended)** | 16GB – 32GB | 8GB+ VRAM | `llama3:8b` | Full cognitive reasoning & tool calling |
| **Heavyweight Enterprise** | 64GB+ | 24GB–48GB VRAM | `llama3:70b` | Complex multi-domain synthesis & architecture |

---

## 🛠️ Step-by-Step Manual Setup

### 1. Clone & Enter Repository
```bash
git clone https://github.com/phass-sphere/phass_sphere.git
cd phass_sphere
```

### 2. Prepare Python Environment (Optional but Recommended)
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note on Zero-Crash Fallbacks**: If any specialized binary or C++ package (e.g. `chromadb`, `playwright`, `pyttsx3`, `sounddevice`, `psutil`) cannot be compiled or installed on your environment, the system gracefully activates its built-in standard-library fallbacks with zero crash.

### 4. (Optional) Install Local Ollama Runtime
If you wish to execute local open-weights models natively:
- **macOS / Linux**: `curl -fsSL https://ollama.ai/install.sh | sh`
- **Windows**: Download installer from [ollama.ai](https://ollama.ai)
- Pull model:
  ```bash
  ollama pull llama3:8b
  ```

---

## 🚀 Running the Assistant (`launch.py`)

The universal launcher provides multiple modes:

### 1. Interactive AI Chat (Default)
```bash
python launch.py --mode chat
```

### 2. Change Personality
Choose from 5 emotional and communicative presets:
```bash
python launch.py --mode chat --personality executive
python launch.py --mode chat --personality friendly
python launch.py --mode chat --personality creative
python launch.py --mode chat --personality late_night
```

### 3. Full-Featured REST API
Starts the multi-channel JSON API on port 8000:
```bash
python launch.py --mode api --port 8000
```
- Test health: `curl http://localhost:8000/health`
- List tools: `curl http://localhost:8000/tools`
- Chat API: `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Hello!"}'`

### 4. Graphical & Holographic Dashboard
```bash
python launch.py --mode dashboard
```

### 5. Floating Desktop Overlay Widget
```bash
python launch.py --mode widget
```

### 6. Background Sentinel (Autonomous Telemetry & Proactive Health)
```bash
python launch.py --mode sentinel
```

### 7. Unified Master Launch (API + Sentinel + Chat)
```bash
python launch.py --mode all
```

---

## 🧹 Codebase Audit & Sanitization
To inspect duplicates, clean temporary caches, and verify directory organization:
```bash
python tools/project_cleaner.py
```
This generates:
- `CLEAN_MANIFEST.json`: Complete file-by-file inventory and checksums.
- `CLEAN_SUMMARY.md`: Codebase hygiene status and architecture breakdown.

---

## 🧪 Running the Verification Test Suite
Ensure all 370+ unit and integration tests pass cleanly:
```bash
pytest tests/ -v
```
