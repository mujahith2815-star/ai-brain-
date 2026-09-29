# =============================================================================
# P.H.A.S.S SPHERE ZENITH v8.0 — WINDOWS ONE-COMMAND QUICKSTART
# Usage: iwr -useb https://.../get_llama.ps1 | iex
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   P.H.A.S.S SPHERE ZENITH v8.0 — WINDOWS DEPLOYMENT ENGINE         " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[!] Python is not found in PATH." -ForegroundColor Red
    Write-Host "    Install Python 3.10+ via winget:" -ForegroundColor Yellow
    Write-Host "    winget install Python.Python.3.12" -ForegroundColor Yellow
    exit 1
}

$pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[+] Detected Python $pyVersion" -ForegroundColor Green

# Run zero-touch auto installer
& python auto_install.py

# Launch interactive chat session
& python launch.py --mode chat
