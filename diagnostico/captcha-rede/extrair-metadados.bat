@echo off
setlocal
if "%~1"=="" (
  powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0extrair-metadados.ps1"
) else (
  powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0extrair-metadados.ps1" -InputPath "%~1"
)
pause
endlocal
