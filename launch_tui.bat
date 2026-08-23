@echo off
title spotDL Interactive TUI
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m spotdl interactive %*
) else (
    python -m spotdl interactive %*
)
