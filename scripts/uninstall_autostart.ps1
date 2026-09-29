<#
.SYNOPSIS
    Uninstalls the Orvix Sphere Windows Scheduled Task.
#>
$ErrorActionPreference = "Continue"

$tasks = @("OrvixSphere_AutoStart", "OrvixSphereDaemon")

foreach ($t in $tasks) {
    Write-Host "[*] Checking Scheduled Task '$t'..." -ForegroundColor Yellow
    $check = schtasks.exe /query /tn $t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[*] Removing Scheduled Task '$t'..." -ForegroundColor Yellow
        schtasks.exe /delete /tn $t /f
        Write-Host "[OK] Task '$t' successfully removed." -ForegroundColor Green
    } else {
        Write-Host "[-] Task '$t' not found (already clean)." -ForegroundColor Gray
    }
}
