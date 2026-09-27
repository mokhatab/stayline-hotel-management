$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[desktop]"

Write-Host ""
Write-Host "Desktop setup complete."
Write-Host "Run it with: .\.venv\Scripts\python.exe desktop\run_desktop.py"