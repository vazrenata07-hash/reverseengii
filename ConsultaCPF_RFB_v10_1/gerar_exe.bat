@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install --upgrade pyinstaller
  py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name ConsultaCPF_RFB consulta_cpf_rfb.py
) else (
  python -m pip install --upgrade pyinstaller
  python -m PyInstaller --noconfirm --clean --onefile --windowed --name ConsultaCPF_RFB consulta_cpf_rfb.py
)
echo.
echo EXE criado em dist\ConsultaCPF_RFB.exe
pause
