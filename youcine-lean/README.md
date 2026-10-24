# YC TV 1.15.4 — Lean v3.5 candidate

Inicializador proprio para o original TV 1.15.4, voltado a Android 9/10.
Esta e uma correcao candidata da falha localizada na coleta de 21 execucoes.
Compilacao, empacotamento e assinatura nao comprovam estabilidade ou trial.
Todos os testes do aplicativo ficam com o usuario.

## Falha localizada

Na coleta 20261023-232203-2761c226, houve quatro SIGSEGV em fases com motor,
incluindo uma em RUNTIME, que nao instala callbacks de app. As pilhas mostram
PC zero e retorno por libycidentity.so+0x50023 ou +0x51952. Os simbolos exatos
da build 73e3ae0 localizam essas chamadas em ClassLinker::ShouldUseInterpreterEntrypoint
e MemberFunction::operator(), usadas por FixupStaticTrampolines.

O helper LSPlant v6.4 instala o desvio por inline_hooker e somente depois
atribui o ponteiro de backup. Uma thread pode entrar no callback enquanto
esse ponteiro ainda esta nulo. O helper tambem retornava sucesso ao encontrar
o simbolo original, mesmo se o backend devolvesse backup nulo.

## Correcao nativa

O patch local substitui os slots de backup por YCReadyBackup. O alvo original
e publicado com release; o callback aguarda e le com acquire antes de invocar
o alvo. Isso cobre ponteiros de funcoes e MemberFunction sem leitura simultanea
da representacao de ponteiro de membro parcialmente escrita. Falhas do backend
passam a ser recusadas em HookSymNoHandle. O backend registra status e ausencia
de backup. Um callback indevido apos uma falha de instalacao nao recebe um
retorno inventado: produz abort explicito, em vez de chamada ao endereco zero.

patch_vendor.py valida o SHA-256 exato do header original antes de aplicar a
alteracao. build_native.py restaura esse arquivo no checkout fixo do LSPlant
e aplica o patch. O header proprio esta em native/yc_ready_backup.hpp.

## Integracao da identidade

A coleta confirmou core.request.bean.SnTokenBean, com vinte parametros String,
int de mascara e sc.g, e o campo fingerprint String. A v3.5 usa esse alvo
diretamente, mascara 0x8000/indice 15 da referencia, validando o formato antes
de instalar o callback. PreInstallAuthBean nao aparece nessa versao;
TerminalAuthBean tem authCode/authVersion/reserve1/openNum e nao tem fingerprint.
Ele nao e usado como substituto do modelo antigo.

As regras passam a ser instaladas no provider, antes de Application.onCreate,
para alcancar autenticacao que possa comecar nessa chamada. A instalacao e
idempotente. A fronteira posterior permanece para registrar o retorno da
Application e eventos de Activity, sem reinstalar os hooks. Isso muda a ordem
das builds anteriores; o efeito nessa versao ainda exige teste do usuario.

O callback gera UUID quando a mascara solicita o fingerprint padrao, preserva
argumentos explicitos e verifica apos o construtor se o UUID chegou ao campo
fingerprint. Registra a primeira invocacao e a mascara sem imprimir o UUID.
Instalacao do hook, execucao e verificacao do campo sao etapas distintas.
Os nomes de parametros nao estavam presentes nos metadados recebidos; a
verificacao do campo e importante para conferir a correspondencia de argumento.

A escrita Properties reconhecida na coleta e o2.g.A. A v3.5 preserva essa regra
com verificacao de formato. A rotina t() vazia da referencia 1.15.1 ainda nao
tem correspondencia comprovada na classe renomeada 1.15.4; ela nao e escolhida
por suposicao. A concessao de novo trial pelo servidor nao foi observada.

## Carregamento preservado

A imagem original assinada continua na pasta externa especifica do app,
validada por SHA-256 e com caminho obtido de /proc/self/fd. Essa e a estrategia
de abertura da v3.2 confirmada pelo usuario. O auxiliar e escolhido pelo ELF
de /proc/self/exe e carregado por um DexClassLoader com pai boot e namespace
nativo separado. Assim o MEmu usa o auxiliar x86_64 junto do ART x86_64 e
mantem a ponte ARM do player.

As quatro bibliotecas permanecem em assets/yc_hooks. Nao ha mudanca nas ABIs
do diretorio lib/ original. O carregador e a biblioteca Dex2C do mod de
terceiros continuam apenas referencias de analise, sem incorporacao ao APK.

## Modos e registros

O padrao da v3.5 e FULL, com as regras habilitadas. O arquivo proprio
diagnostic.properties em getExternalFilesDir("yc_lean") ainda permite OFF,
BOUNDARY, RUNTIME, BEANS, PROPERTIES ou FULL para comparacoes controladas.
O arquivo e lido uma vez por processo. O coletor antigo instala sua propria
build v3.4.2-debug; ele nao serve para confirmar que a v3.5 esta instalada.

O diario JSONL conserva versao, PID, identificador e etapas. Inventario completo
de classes e schemas detalhados ficam restritos a runs de diagnostico, evitando
varredura extensa na abertura normal. A release inclui simbolos nativos nao
removidos e build-identity.json para simbolicar os offsets do binario exato.

## Compilar

Linux, Python 3.11+, JDK 17/21, Git, CMake 3.31, Ninja, NDK 26.3.11579264:

```sh
export ANDROID_NDK_HOME=/caminho/android-sdk/ndk/26.3.11579264
python3 build_native.py
python3 build.py
```

Saida: build/yc-tv-1.15.4-lean-v3.5.apk. O workflow publica APK, fontes,
checksums, identidade do build e simbolos. Nenhum teste do app e executado.

## Fontes e dependencias

| Componente | Revisao | Licenca |
| --- | --- | --- |
| LSPlant v6.4 + patch local | 7217ac6f41e2bda549e4acb54e632abb03e5ccaf | LGPL-3.0 |
| DexBuilder | 9d57844a301077abf4c29e061b2458c56a363c8f | LGPL-3.0 |
| Dobby | 9c85e74f92eda36b99ddb0fddb17a9df2278a4d3 | Apache-2.0 |
| liblzma/XZ 5.4.6 | 6e8732c5a317a349986a4078718f1d95b67072c5 | ver COPYING-XZ.txt |

Fontes upstream: https://github.com/LSPosed/LSPlant,
https://github.com/LSPosed/DexBuilder, https://github.com/jmpews/Dobby,
https://github.com/tukaani-project/xz. As licencas estao em licenses/ e no APK.
As fontes proprias e o patch sao LGPL-3.0-or-later; os componentes externos
mantem seus termos. O APK original tem SHA-256
5629c0dc0dc0b631f09bd21f81a5d671e64e6d516cb4a28a9b9fb45a2971b231.
