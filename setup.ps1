$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectDir

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
& .\.venv\Scripts\python.exe main.py --init

Write-Host "Proyecto preparado. Ejecuta:"
Write-Host ".\.venv\Scripts\python.exe main.py --update"
Write-Host ".\.venv\Scripts\python.exe main.py --open"

