@echo off
title Create P.H.A.S.S AI Model in Ollama
echo ========================================================
echo   BUILDING P.H.A.S.S AI MODEL IN OLLAMA (FROM MODELFILE)
echo ========================================================
echo.
echo [*] Running: ollama create phass -f Modelfile
ollama create phass -f Modelfile
echo.
if %ERRORLEVEL% EQU 0 (
    echo [+] P.H.A.S.S AI Model created successfully in Ollama!
    echo [+] You can now launch it anytime with: ollama run phass
    echo.
    echo [*] Launching P.H.A.S.S in Ollama now...
    ollama run phass
) else (
    echo [!] Ollama create failed or Ollama is not running.
    echo [*] You can also run P.H.A.S.S instantly using: python run_model_dashboard.py or python run_model_chat.py
)
pause
