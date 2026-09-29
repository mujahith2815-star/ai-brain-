<#
.SYNOPSIS
    Orvix Sphere Windows Production Installer Script
#>
param (
    [switch]$AutoStart,
    [switch]$SkipModelDownload
)

$ErrorActionPreference = "Stop"
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "             ORVIX SPHERE SYSTEM INSTALLER (WINDOWS)             " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "[1/5] Verifying Python Runtime..." -ForegroundColor Yellow
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Host "  [✓] Detected Python $pyVer" -ForegroundColor Green
} catch {
    Write-Error "Python 3.10 or higher is required. Please install Python and ensure it is on PATH."
}

# 2. Setup Virtual Environment
Write-Host "[2/5] Initializing Python Virtual Environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  [✓] Created .venv" -ForegroundColor Green
} else {
    Write-Host "  [✓] Existing .venv found." -ForegroundColor Green
}

# 3. Install Dependencies
Write-Host "[3/5] Installing Dependencies from requirements.txt..." -ForegroundColor Yellow
& .\.venv\Scripts\pip.exe install -r requirements.txt --quiet
Write-Host "  [✓] All dependencies verified." -ForegroundColor Green

# 4. Initialize Storage & Memory Databases
Write-Host "[4/5] Initializing Storage and Knowledge Databases..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -c "from knowledge.sqlite_store import KnowledgeStore; KnowledgeStore(); print('  [✓] SQLite databases initialized.')"

# 5. Auto-Start Task Registration
if ($AutoStart) {
    Write-Host "[5/5] Registering Windows Login Scheduled Task..." -ForegroundColor Yellow
    & powershell.exe -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1
} else {
    Write-Host "[5/5] Skipping Auto-Start registration. (Use -AutoStart to enable)." -ForegroundColor Gray
}

Write-Host "`n[★] Installation Completed Successfully!" -ForegroundColor Green
Write-Host "To start the chat:           .\.venv\Scripts\python.exe run_model_chat.py" -ForegroundColor Cyan
Write-Host "To launch the Web Dashboard: .\.venv\Scripts\python.exe -m web.launcher" -ForegroundColor Cyan
