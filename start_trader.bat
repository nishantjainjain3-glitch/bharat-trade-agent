@echo off
title Bharat Trade Agent - Autonomous Execution Engine
cd /d "%~dp0"
echo ===================================================
echo   Bharat Trade Agent - Autonomous Live Engine
echo ==================================================
echo Starting agent on http://localhost:8000 ...
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000
pause
