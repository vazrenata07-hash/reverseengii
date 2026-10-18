@echo off
setlocal
echo Feche todas as janelas do Mint antes de continuar.
echo Deixe este BAT e o PS1 na mesma pasta do executavel Mint V24 ou V23.
echo O teste abre o Mint, recarrega a aba 888 e coleta erros por 25 segundos.
echo O log fica nesta pasta. Nada e enviado pela ferramenta de diagnostico.
pause
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnosticar-mint.ps1"
echo.
echo Feche o Mint para encerrar a porta local de diagnostico.
pause
endlocal
