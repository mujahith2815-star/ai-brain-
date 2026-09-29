<#
.SYNOPSIS
    Installs Orvix Sphere as an automated Windows Task on user logon.
.PARAMETER ExePath
    Optional path to the compiled orvix_sphere.exe binary.
#>
param(
    [string]$ExePath = ""
)

$ErrorActionPreference = "Continue"
$taskName = "OrvixSphere_AutoStart"
$projectDir = (Get-Item $PSScriptRoot).Parent.FullName

if (-not [string]::IsNullOrWhiteSpace($ExePath) -and (Test-Path $ExePath)) {
    $targetExe = (Resolve-Path $ExePath).Path
    $cmdArg = "\`"$targetExe\`" --daemon"
    Write-Host "[*] Configuring task using standalone binary: $targetExe" -ForegroundColor Cyan
} else {
    $distExe = Join-Path $projectDir "dist\orvix_sphere.exe"
    if (Test-Path $distExe) {
        $targetExe = (Resolve-Path $distExe).Path
        $cmdArg = "\`"$targetExe\`" --daemon"
        Write-Host "[*] Detected standalone binary: $targetExe" -ForegroundColor Cyan
    } else {
        $pythonExe = Join-Path $projectDir ".venv\Scripts\python.exe"
        $daemonScript = Join-Path $projectDir "cli\daemon.py"
        if (-not (Test-Path $pythonExe)) {
            $pythonExe = "python.exe"
        }
        $cmdArg = "\`"$pythonExe\`" \`"$daemonScript\`" --daemon"
        Write-Host "[*] Using Python daemon script: $daemonScript" -ForegroundColor Cyan
    }
}

Write-Host "[*] Registering Scheduled Task '$taskName'..." -ForegroundColor Cyan

# Attempt 1: Elevated (/rl highest)
$out = & schtasks.exe /create /tn $taskName /tr $cmdArg /sc onlogon /rl highest /f 2>&1
if ($LASTEXITCODE -ne 0) {
    # Attempt 2: Standard user privilege (non-admin)
    Write-Host "[*] Elevated privilege creation unavailable, registering with standard user privileges..." -ForegroundColor Yellow
    $out = & schtasks.exe /create /tn $taskName /tr $cmdArg /sc onlogon /f 2>&1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Task '$taskName' registered to run on login." -ForegroundColor Green
} else {
    Write-Host "[!] Failed to register scheduled task: $out" -ForegroundColor Red
}
