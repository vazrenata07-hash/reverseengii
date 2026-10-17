@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 consulta_cpf_CAPTCHA_COMPACTO_v10_3.py
) else (
  python consulta_cpf_CAPTCHA_COMPACTO_v10_3.py
)
if errorlevel 1 pause
