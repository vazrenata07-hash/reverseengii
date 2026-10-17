@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 consulta_cpf_SO_CAPTCHA_v10_4_1.py
) else (
  python consulta_cpf_SO_CAPTCHA_v10_4_1.py
)
if errorlevel 1 pause
