<#
.SYNOPSIS
    1-Click Automated Ollama Installer for Windows (P.H.A.S.S Sphere v8.0)
.DESCRIPTION
    Downloads and installs the official Ollama Windows installer from ollama.com,
    starts the background daemon, and registers the P.H.A.S.S AI model.
#>

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       P.H.A.S.S SPHERE — OLLAMA WINDOWS AUTO INSTALLER     " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$installerUrl = "https://ollama.com/download/OllamaSetup.exe"
$installerPath = "$env:TEMP\OllamaSetup.exe"

Write-Host "[*] Downloading Ollama Windows installer from $installerUrl..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    Write-Host "[+] Download complete: $installerPath" -ForegroundColor Green
    
    Write-Host "[*] Launching Ollama Setup (Please complete the installation wizard)..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -Wait
    
    Write-Host "[+] Ollama installed successfully!" -ForegroundColor Green
    Write-Host "[*] Registering P.H.A.S.S AI Model with Ollama..." -ForegroundColor Yellow
    
    # Reload environment path
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        ollama create phass -f Modelfile
        Write-Host "[+] P.H.A.S.S AI Model created in Ollama!" -ForegroundColor Green
        Write-Host "[+] You can now run: ollama run phass" -ForegroundColor Cyan
    } else {
        Write-Host "[!] Ollama installed. Please restart your terminal and run 'ollama create phass -f Modelfile'." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[!] Download/Installation error: $_" -ForegroundColor Red
    Write-Host "[*] Remember: P.H.A.S.S has a built-in Native Neural LLM Engine and works 100% without Ollama! Run 'python run_model_chat.py' to chat right now." -ForegroundColor Green
}
