@echo off
title Orvix Sphere v1.0.0 Chat Interface
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_model_chat.py %*
) else (
    python run_model_chat.py %*
)
pause
