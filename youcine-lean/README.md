# YC TV 1.15.4 — Lean v3.3.2 experimental

## Correcao v3.3.2

A coleta `20261023-181826-899` confirma o APK exato v3.3.1. A descoberta
pelos mapas funcionou (`phdr=0 maps=5`), mas o motor encontrou apenas 17
simbolos e falhou em GetMethodShorty. Os mapas mostram o auxiliar ARM64 em
code_cache/yc_identity/arm64-v8a, executado por Houdini, enquanto o ART do
processo e x86_64. O libart.so copiado pelo ADB tem 29 secoes e o simbolo
GetMethodShorty; a leitura pelo auxiliar traduzido registrou 11 secoes.

A v3.3.2 determina a arquitetura pelo ELF de /proc/self/exe em Java, sem
usar os.arch para escolher a biblioteca. Carrega EngineEntry por um
DexClassLoader separado com pai boot e diretorio nativo da arquitetura da
VM. Isso evita herdar o namespace ARM do aplicativo no carregamento do
auxiliar. EngineEntry carrega a biblioteca e registra explicitamente os
metodos JNI das classes de regras por RegisterNatives. O loader e mantido
vivo durante o processo. O carregador original e a ponte ARM do player
continuam preservados.

Os registros das regras passam pela ponte JNI de log depois do carregamento;
a coleta anterior nao mostrou mensagens Java dessa fase, embora contivesse
as mensagens nativas. O log distingue ABI do auxiliar, motor pronto, vinculos
JNI, instalacao de regras e primeira execucao. Nao foram executados testes do
aplicativo: a inicializacao do motor e o efeito das regras ainda dependem
do teste do usuario.

## Correcao v3.3.1

O log fornecido apos a v3.3 registra duas vezes `ART symbols unavailable;
identity rules disabled`. Isso confirma que o auxiliar nativo carregou mas
desativou a rotina antes de instalar os callbacks. O log antigo nao distinguia
localizacao da biblioteca, abertura do ELF e leitura dos simbolos.

A v3.3.1 acrescenta descoberta de libart pelos mapas do proprio processo,
com calculo do load bias pelos segmentos PT_LOAD e verificacao da arquitetura
ELF. Mantem dl_iterate_phdr como outra origem; namespaces do linker podem
restringir sua enumeracao. Registra separadamente candidatos encontrados,
falha de abertura/leitura, ABI divergente e quantidade de simbolos extraidos.
O log recebido comprova a etapa desativada, mas nao identifica sozinho qual
das subetapas falhou. A abertura externa do original da v3.2 e preservada.

Base: `yc_1.15.4_ycsite.apk`, release `2.01` deste repositório. Android 9/10.
O usuário confirmou que a v3.2 abriu, mas sua rotina de identidade não teve o
efeito esperado. A v3.3 preserva a estratégia de abertura e muda essa rotina.

## Abertura preservada

O APK original assinado continua na pasta externa específica do aplicativo,
obtida por `getExternalFilesDirs("yc_lean")`, validado por tamanho e SHA-256.
O caminho real continua obtido por `Os.readlink("/proc/self/fd/" + fd)` antes
da delegação à fábrica original. Isso conserva a solução da v3.2 para o layout
rejeitado por `libexec.so+0x48c10`: caminho iniciando em `/data/` e contendo
`/com.world.youcinetv/`. O adaptador local de assinatura também permanece.

Não foram incorporados o carregador nem a biblioteca Dex2C do mod de terceiros.

## Rotina nova

A v3.2 persistia um UUID e o atribuía a `Build.FINGERPRINT`. Isso não reproduzia
o mod: ele gera UUID no argumento padrão `fingerprint` de dois objetos de
autenticação. A v3.3 remove a identidade persistida e a atribuição global.

| Objeto | Parâmetro fingerprint, índice zero | Máscara padrão |
| --- | --- | --- |
| PreInstallAuthBean | 17 | 0x20000 |
| SnTokenBean | 15 | 0x8000 |

O novo callback fornece `UUID.randomUUID().toString()` quando a máscara
solicita o fingerprint padrão, limpa somente esse bit e chama o construtor
original. Cada construção nesse caminho recebe um UUID próprio. Valores
explicitamente passados pelo chamador são preservados. Android ID, MAC e
serial não são randomizados: o código examinado do mod consulta o sistema.

A rotina de escrita Properties de três argumentos String, vazia no mod,
também passa a ser omitida quando sua classe correspondente é localizada.
O reconhecimento verifica formato dos campos e métodos; resultado ausente
ou ambíguo é registrado e não recebe alteração. A rotina `t()` vazia só é
interceptada se a classe ainda for `i2.f` com o formato esperado. O código não
apaga arquivos globais nem presume que todas as chaves de sessão sejam cache.

O motor de interceptação é LSPlant v6.4 com Dobby; as regras Java, ponte JNI e
leitor dos símbolos ELF de ART são deste projeto. O leitor inclui suporte a
`.gnu_debugdata` por liblzma. Um ContentProvider privado inicia as regras
depois de Application.attach e antes de Application.onCreate. Há tentativas
limitadas adicionais nos primeiros eventos de Activity se os objetos ainda
não estiverem visíveis. O auxiliar é compilado para ARM32, ARM64, x86 e x64.

As quatro bibliotecas ficam em `assets/yc_hooks/`, com SHA-256, e só a versão
correspondente à VM é extraída para code_cache. Não se adicionam novas ABIs ao
diretório `lib/` do APK: isso preserva a seleção das bibliotecas originais e
a ponte ARM usada pelo player no MEmu. A dependência dessa ponte permanece.

## Estado da entrega

A análise estática detalhada está em
[COMPARACAO-IDENTIDADE.md](../youcine-diagnostico/COMPARACAO-IDENTIDADE.md).
O mod de referência é 1.15.1; a base nova é 1.15.4, cujo código protegido de
autenticação não foi extraído. Por isso os hooks exigem as assinaturas e os
campos esperados. Os logs `YCLean` distinguem inicialização do motor, instalação
dos callbacks e primeira aplicação de fingerprint, sem imprimir os valores.

Compilar, empacotar e assinar não confirmam a abertura ou o efeito no servidor.
Não foram executados testes do aplicativo; todos os testes nos dispositivos
ficam com o usuário. A abertura da v3.2 foi confirmada pelo usuário; a nova
ponte nativa e as regras da v3.3 ainda precisam dessa confirmação. Uma nova
identidade local não comprova concessão de novo trial pelo servidor.

## Compilar

Linux, Python 3.11+, JDK 17/21, Git, CMake 3.31, Ninja e Android NDK
26.3.11579264. As fontes externas são obtidas em commits fixos por
`build_native.py`; o build não executa testes.

```sh
export ANDROID_NDK_HOME=/caminho/para/android-sdk/ndk/26.3.11579264
python3 build_native.py
python3 build.py
```

Saída: `build/yc-tv-1.15.4-lean-v3.3.2.apk`. O workflow `YC TV Lean Build`
compila as quatro arquiteturas, empacota, assina e publica APK, SHA-256 e
fontes na release `yc-tv-1.15.4-lean-v3.3.2`.

## Dependências e fontes

| Componente | Revisão | Fonte/licença |
| --- | --- | --- |
| LSPlant v6.4 | 7217ac6f41e2bda549e4acb54e632abb03e5ccaf | https://github.com/LSPosed/LSPlant — LGPL-3.0 |
| DexBuilder, submódulo LSPlant | 9d57844a301077abf4c29e061b2458c56a363c8f | https://github.com/LSPosed/DexBuilder — LGPL-3.0 |
| Dobby | 9c85e74f92eda36b99ddb0fddb17a9df2278a4d3 | https://github.com/jmpews/Dobby — Apache-2.0 |
| liblzma/XZ 5.4.6 | 6e8732c5a317a349986a4078718f1d95b67072c5 | https://github.com/tukaani-project/xz — ver COPYING-XZ.txt |

Os textos estão em `licenses/` e também no APK. As fontes próprias desta
entrega são disponibilizadas sob LGPL-3.0-or-later; os componentes externos
mantêm seus termos. Os scripts e revisões permitem recompilar e substituir
as bibliotecas sem reutilizar binários do mod. O aplicativo original e seus
componentes mantêm seus termos próprios.
