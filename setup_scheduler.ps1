param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$MainScript = Join-Path $ProjectDir "main.py"
$TaskName = "RadarMazosMarvelSnap"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarea eliminada: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Primero ejecuta .\setup.ps1"
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument ('"{0}" --update' -f $MainScript) -WorkingDirectory $ProjectDir
$TriggerMorning = New-ScheduledTaskTrigger -Daily -At "10:00"
$TriggerEvening = New-ScheduledTaskTrigger -Daily -At "19:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($TriggerMorning, $TriggerEvening) -Settings $Settings -Description "Actualiza el radar local de mazos Marvel Snap" -Force | Out-Null
Write-Host "Tarea programada a las 10:00 y 19:00: $TaskName"

