@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install --upgrade pyinstaller
  py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name ConsultaCPF_RFB_SO_CAPTCHA_v10_4 consulta_cpf_SO_CAPTCHA_v10_4.py
) else (
  python -m pip install --upgrade pyinstaller
  python -m PyInstaller --noconfirm --clean --onefile --windowed --name ConsultaCPF_RFB_SO_CAPTCHA_v10_4 consulta_cpf_SO_CAPTCHA_v10_4.py
)
echo.
echo EXE criado em dist\ConsultaCPF_RFB_SO_CAPTCHA_v10_4.exe
pause
