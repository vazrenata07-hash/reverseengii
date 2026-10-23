# Diagnostico da integracao v3.3.1

Instale a v3.3.1 antes da coleta: ela acrescenta a descoberta do ART pelos
mapas e mensagens por subetapa para a falha observada na v3.3.

Execute `Diagnosticar-Rotina-YouCine.cmd` no Windows ou:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\Diagnosticar-Rotina-YouCine.ps1"
```

O coletor usa o ADB do MEmu e o serial `127.0.0.1:21503`. Procura adb.exe na
pasta atual, na pasta do script, nos caminhos padrao do MEmu e no PATH.
Para outro caminho ou instancia, use `-Adb 'D:\MEmu\adb.exe' -Serial '127.0.0.1:21513'`.

O app e reaberto com os dados preservados. Durante 60 segundos, navegue ate o
aviso de expirado. Depois o coletor encerra seu proprio processo de logcat,
mantem o app aberto e gera `youcine-rotina-DATA-HORA.zip` no Desktop.
`-Seconds 90` muda o periodo; `-SemReiniciar` observa o processo atual, podendo
nao capturar as mensagens de inicializacao necessarias.

Inclui:

- Identificacao do APK instalado por SHA-256, comparada a v3.3.1 publicada.
- Android, ABIs e configuracao da ponte nativa; metadados do pacote e providers.
- Historico anterior separado dos registros da nova execucao.
- Logs filtrados YCLean/LSPlant/Dobby e falhas Java/linker/libc.
- PIDs e bibliotecas relevantes, quando o usuario ADB pode ler os mapas.
- Copias das bibliotecas publicas libart.so do Android, quando legiveis, para
  inspecionar os simbolos ELF sem uma segunda coleta. Nao e um dump de memoria.
- RESUMO.txt e etapas.json, separando instalacao de callbacks e uso observado.

O marcador delimita a execucao nova para evitar aproveitar mensagens antigas
como prova de sucesso. Ausencia de evento nao prova a causa de falha; callbacks
executados nao comprovam o resultado do servidor. O coletor nao le arquivos
privados de sessao, nao instala APK, nao limpa dados/cache/logcat, nao modifica
as regras do app e nao solicita root. Se uma etapa falhar, tenta gerar ZIP parcial.

Este coletor foi escrito para execucao pelo usuario. Nao foram executados
testes de dispositivo, emulador ou PowerShell pelo agente.

## Achado do log recebido

O arquivo `youcine-rotina.txt` fornecido registra em duas inicializacoes da
v3.3 `ART symbols unavailable; identity rules disabled`. O auxiliar nativo
carregou, mas nao encontrou os simbolos necessarios e desativou as regras.
Isso impede atribuir o resultado do VIP a callbacks ativos. O log nao
discrimina enumeracao, abertura do ELF e leitura dos simbolos; a v3.3.1
acrescenta descoberta pelos mapas e mensagens dessas subetapas.
