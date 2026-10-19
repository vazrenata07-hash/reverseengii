@echo off
setlocal
cd /d "%~dp0"
echo Feche todas as janelas do Mint antes de continuar.
echo Deixe este BAT e o PS1 junto do EXE. A maior versao VNN sera escolhida.
echo Quando aparecer CAPTURA ATIVA, abra somente o formulario de cadastro.
echo Nao preencha nem envie o formulario. Nao crie conta e nao faca login.
echo Aguarde os 60 segundos sem recarregar a pagina.
echo O diagnostico gera um TXT local, sem tokens ou dados da conta.
pause
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnosticar-sdk-cadastro.ps1"
echo.
echo Feche o Mint apos a coleta para encerrar a porta local de diagnostico.
pause
endlocal
