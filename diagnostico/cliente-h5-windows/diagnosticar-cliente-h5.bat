@echo off
setlocal
echo Feche todas as janelas do Mint antes de continuar.
echo Deixe este BAT e o PS1 na mesma pasta do executavel Mint V24 ou V23.
echo O teste recarrega a aba 888, observa por 25s e le trechos JS por ate 45s.
echo Nao faca login nem jogue durante a coleta. Revise o log antes de compartilhar.
echo O ZIP fica nesta pasta e contem log e arquivos JS externos do site.
echo Nada e enviado pela ferramenta. HTML, cookies e armazenamento nao sao salvos.
pause
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnosticar-cliente-h5.ps1"
echo.
echo Feche o Mint para encerrar a porta local de diagnostico.
pause
endlocal
