@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero haz doble clic en INSTALAR.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py --update
if errorlevel 1 (
  echo La actualizacion ha fallado. Revisa radar_mazos.log
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py --open
