# Depuracao por fases - v3.4.2-debug

Extraia o ZIP e execute `Depurar-YouCine.cmd`. O coletor localiza o ADB do
MEmu, usa `127.0.0.1:21503`, baixa a build exata v3.4.2-debug e verifica seu
SHA-256. Atualiza por `adb install -r`, preservando dados. Uma falha de
assinatura/instalacao interrompe a comparacao; nao desinstala o aplicativo.

Depois do download, a comparacao leva aproximadamente cinco a sete minutos.
O coletor abre e encerra o app automaticamente em sete fases, com tres
aberturas de 12 segundos por fase (21 execucoes ao todo). A repeticao trata
a intermitencia informada pelo usuario: duas falhas seguidas de uma abertura.

| Fase | Conteudo ativo |
| --- | --- |
| OFF inicial | Carregador/imagem originais e diario; sem motor/fronteira |
| BOUNDARY | Fronteira apos Application.onCreate; sem motor |
| RUNTIME | Inicializacao LSPlant, sem callbacks de app |
| BEANS | Motor e callbacks dos beans |
| PROPERTIES | Motor e callback de persistencia |
| FULL | Motor e ambas as familias de callbacks |
| OFF final | Repete a base para observar diferencas de estado |

O resultado e `youcine-depuracao-DATA-HORA.zip` no Desktop. Envie esse ZIP.
Os testes no dispositivo sao feitos pelo usuario. O agente prepara as
fontes, compila, empacota e assina, sem executar o aplicativo ou o coletor.

## O que a coleta permite conferir

- APK instalado por SHA-256, versao do coletor, Android, ABIs e ponte nativa.
- Modo e identificador que o app efetivamente leu em cada processo.
- Diario JSONL persistente, independente do filtro de Logcat, com PID/TID,
  tempos, fronteiras, excecoes e ultima etapa concluida.
- Pilhas completas Java e nativas, buffer crash antes/depois e tombstones
  novos/alterados do pacote, quando o usuario ADB consegue le-los.
- Mapas, estado/espera do processo, foco da janela e nomes das classes dos
  DEX, sem leitura de arquivos privados de sessao.
- Na fase FULL, campos, assinaturas dos construtores e anotacao Kotlin dos
  beans relacionados a autenticacao, sem instanciar objetos nem ler seus valores.
- Bibliotecas publicas libart.so para analisar os simbolos reais do sistema.

A release do APK inclui simbolos nativos exatos e build-identity.json, para
simbolicar offsets usando o mesmo commit e auxiliar do APK publicado.

OFF mantem nosso carregador e provider; nao equivale ao APK original intacto.
RUNTIME ainda modifica rotinas internas de ART pela inicializacao do motor.
Os mesmos dados/caches sao usados entre fases e a ordem pode influenciar o
resultado. O relatorio distingue app vivo, Activity retomada e crash observado;
nao transforma ausencia de registro em prova de sucesso nem afirma uma causa
unica automaticamente.

## Encerramento e parametros

O coletor nao limpa dados/cache/logcat nem solicita root. Usa apenas o acesso
que o ADB ja possui. O app e encerrado no fim. O arquivo proprio de controle
e restaurado ou removido; os diarios dessa coleta permanecem para depuracao.
A build instalada permanece no aparelho, com modo padrao OFF.

Para mudar instancia/caminho ou periodo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Depurar-YouCine.ps1 -Adb 'D:\MEmu\adb.exe' -Serial '127.0.0.1:21513' -Seconds 25
```

`-SkipInstall` exige que o SHA-256 da build instalada ja corresponda ao
esperado. Erros produzem um ZIP parcial quando possivel. O coletor encerra
somente seu processo cliente de Logcat, sem reiniciar o servidor ADB.
`-Repetitions 1` permite uma coleta curta, mas nao cobre o padrao intermitente
observado. Cada tentativa tem run ID e diarios proprios; reinicios dentro
da mesma tentativa preservam os registros dos PIDs anteriores.
