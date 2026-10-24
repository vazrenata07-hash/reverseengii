# Depuracao do APK instalado do mod original

Use `Diagnosticar-Mod-Original.ps1` no Windows PowerShell 5.1 com o MEmu aberto.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Diagnosticar-Mod-Original.ps1
```

O destino padrao e `127.0.0.1:21503`. O script encontra o ADB na pasta atual,
na pasta do MEmu ou no PATH. Para outra instancia, informe `-Serial`; para
outra instalacao do ADB, informe `-Adb`.

O coletor encerra o processo atual e faz uma abertura do APK ja instalado,
observando por 25 segundos. Nao instala APK, nao limpa dados, nao muda
as configuracoes do carregador e nao apaga os buffers de logcat.

Coleta logcat completo, buffer de crash antes/depois, hash do APK instalado,
manifesto resolvido pelo sistema, arquitetura efetiva, propriedades de
traducao nativa, mapas e estado do processo, estado das atividades e memoria.
Com acesso permitido, copia tombstones novos do app e bibliotecas ART/bridge
do sistema para resolver offsets das pilhas nativas. Falhas de permissao
ficam registradas; nao impedem as demais coletas.

O ZIP `youcine-mod-crash-<data-hora>-<id>.zip` fica no Desktop.
Envie o ZIP completo. Nao e preciso executar `logcat -c`, reinstalar o app
ou repetir o procedimento para cada arquivo coletado.

Este script e independente dos coletores por fases do projeto Lean.
Pode ser usado tanto com o APK de terceiros original quanto com compat-v1;
o hash instalado identifica qual deles foi observado. Nenhum teste de
execucao foi realizado pelo autor do coletor; a execucao fica com o usuario.
