# Orvix Sphere Zenith v1.0.0 Release Notes

**Release Date:** September 15, 2026  
**Codename:** Zenith  
**Architecture:** Dual-Brain Cognitive Engine + Autonomous Sentinel Protocol  

---

## Executive Summary

Orvix Sphere v1.0.0 represents the first production-grade standalone release of the sovereign physical AI and cognitive operating system. Operating locally on CPU without requiring external API keys or cloud dependencies, Orvix Sphere unites dual-model inference, Model Context Protocol (MCP) server integration, proactive edge-triggered background tasks, persistent RAG knowledge vaults, hands-free voice control, and a real-time web dashboard into a single distributable platform.

---

## The 5 Core Subsystems

### 1. Knowledge & RAG Memory Vault (`knowledge/`)
- **Dual-Store Architecture**: SQLite (`agent_memory.db`) provides deterministic key-value fact persistence and named lists; dense vector embeddings provide semantic similarity retrieval.
- **Cross-Session Durability**: Ingested facts and documents survive process termination and system reboots.
- **Zero-Friction Ingestion**: Dedicated inbox folder watcher automatically indexes incoming text, markdown, and code snippets into the vector store upon arrival.

### 2. Voice Intelligence Suite (`voice/`)
- **Speech Synthesis**: Real-time pyttsx3 SAPI5 local speech synthesis with adaptive speech rate.
- **Speech Recognition**: Local OpenAI Whisper speech-to-text with graceful text-fallback guards when microphone hardware is absent.
- **Hands-Free Wake Detection**: Configurable wake word engine with keyboard hotkey fallbacks.

### 3. Model Context Protocol Integration (`mcp/`)
- **Native Protocol Client**: Discovers and coordinates external tool servers via standard JSON-RPC over stdio.
- **Bundled Servers**: Pre-configured SQLite database inspector, local filesystem navigator, and HTTP fetch engine.
- **Dynamic Adapter**: Transparently maps discovered MCP server tools into the Llama ReAct agent tool catalog as `mcp__<server>__<tool>`.

### 4. Proactive Autonomous Sentinel (`proactive/`)
- **Trigger-Driven Scheduler**: Parses declarative `triggers.json` supporting cron-based periodic intervals, filesystem change events, and system condition thresholds.
- **Safety & Operator Approval**: High-risk operations (destructive commands, file overwrites) are automatically intercepted and held in the operator approval queue (`/queue`).
- **Emergency Kill Switch**: Operator commands (`/pause`, `/resume`) instantly freeze or re-arm autonomous background operations.

### 5. Production Web Dashboard & Diagnostics (`web/`, `diagnostics/`)
- **Real-Time FastAPI Web UI**: Dark-mode glassmorphic dashboard with live WebSockets, streaming chat, and interactive queue approval cards.
- **System Doctor (`/doctor`)**: 10-point comprehensive diagnostic scanner providing real-time telemetry on Python runtime, package dependencies, SQLite, vector vaults, MCP servers, and proactive sentinels.

---

## System Requirements & Hardware Guidelines

| Component | Minimum Requirement | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 (64-bit) | Windows 11 (64-bit) |
| **Processor (CPU)** | x86_64 Dual-Core (>= 2.0 GHz) | x86_64 4-Core or higher |
| **System Memory (RAM)** | 4 GB | 8 GB or 16 GB |
| **Storage (Disk)** | 4 GB free space (including weights) | 10 GB free space (SSD recommended) |
| **Python Runtime** | None required (for standalone .exe) | Python 3.10+ (for source installation) |
| **Node.js** | Optional (bundled MCP features) | Node.js 18+ LTS |

---

## Known Limitations (v1.0.0)

1. **CPU-First Inference**: Local model inference uses PyTorch CPU float32 tensors (~1.5 tokens/sec for Llama-3.2-1B). GPU acceleration (CUDA / ROCm) is not enabled in this baseline build.
2. **Platform Focus**: The standalone executable and installer are tailored specifically for Windows (x64). Linux and macOS support is currently source-based via `installer/install.sh`.

---

## Roadmap for v1.1.0

- **GPU Acceleration**: Optional Vulkan and DirectML / CUDA backends for high-speed local inference (>20 tok/sec).
- **Cross-Platform Installers**: Native `.deb`, `.rpm`, and macOS `.pkg` installers.
- **Mobile Companion Web App**: Progressive Web App (PWA) manifest for remote LAN dashboard control.
- **Multi-Modal Vision**: Screen analysis and clipboard screenshot question-answering.
