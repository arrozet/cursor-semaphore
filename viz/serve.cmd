@echo off
REM Cross-platform entry for Windows. Prefer: python viz\serve.py
cd /d "%~dp0\.."
python viz\serve.py %*
