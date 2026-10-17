@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 consulta_cpf_rfb.py
) else (
  python consulta_cpf_rfb.py
)
if errorlevel 1 pause
