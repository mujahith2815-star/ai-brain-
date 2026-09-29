# Orvix Sphere User Guide

Welcome to Orvix Sphere Zenith. This guide covers setup, chat, voice, web dashboard, and proactive operation.

## 1. Getting Started
Run the first-time setup wizard:
```powershell
python setup_wizard.py
```
This configures your operator name, model preferences, and watch folders.

## 2. Using the Web Dashboard
Launch the dashboard:
```powershell
python -m web.launcher
```
- **Chat Panel**: Interactive chat with markdown rendering and speech recognition.
- **Telemetry Grid**: Real-time status of Llama, Phi-4, MCP, and Proactive subsystems.
- **Approval Queue**: Inspect destructive or risky actions with one-click Approve/Reject buttons.

## 3. Voice Controls
- Say `"Hey Orvix"` or press `Ctrl+Shift+O` to speak.
- Type `/voice on` or `/voice off` to toggle audio responses.
- Type `/voice loop` for hands-free continuous conversation.

## 4. Proactive Mode & Safety Guardrails
- **Activation**: Type `/proactive on`. Confirm when prompted.
- **Kill Switch**: Type `/pause` to immediately freeze all background actions. Type `/resume` to unfreeze.
- **Approvals**: Actions involving destructive operations appear in `/queue`. Run `/approve <id>` to execute.
