@echo off
title Nova Bot setup
cd /d "%~dp0"
echo.
echo   Nova Bot setup
echo   --------------
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo   Python isn't installed. Installing it now...
  winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements --silent
  set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%PATH%"
)

where ollama >nul 2>nul
if errorlevel 1 (
  if not exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    echo.
    echo   Ollama lets Nova Bot run AI models on this PC, private and offline.
    choice /c YN /m "  Install Ollama too"
    if not errorlevel 2 winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements --silent
  )
)

echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\make_shortcut.ps1"
echo.
echo   Done. Open "Nova Bot" from your Desktop or Start menu.
echo.
start "" pythonw "%~dp0server.py" --open
pause
