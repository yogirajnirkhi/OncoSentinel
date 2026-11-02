@echo off
REM OncoSentinel v2.0 — Windows Command Prompt Startup Script
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "V1_DIR=%ROOT_DIR%\v1"
set "PYTHONPATH=%V1_DIR%"

echo ============================================================
echo   OncoSentinel v2.0 — Unified Clinical AI ^& HMS Platform
echo ============================================================
echo   Portal ^& HMS Workspace : http://127.0.0.1:8000
echo   Interactive API Docs   : http://127.0.0.1:8000/docs
echo ============================================================

pushd "%V1_DIR%"
python run.py
popd
