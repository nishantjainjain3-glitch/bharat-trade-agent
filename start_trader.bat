@echo off
title Bharat Trade Agent - Autonomous AI Trading Workstation
color 0A
cd /d "C:\Users\HP\.gemini\antigravity\scratch\indian-trading-agent"

echo =====================================================================
echo           BHARAT TRADE AGENT - AUTONOMOUS AI WORKSTATION
echo =====================================================================
echo.
echo   * Initializing environment and Angel One SmartAPI connection...
echo   * Dashboard will automatically open in your default browser.
echo.
echo =====================================================================

start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)

echo.
echo Agent process terminated.
pause
