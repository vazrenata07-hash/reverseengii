# YC TV 1.15.4 — Lean v3.1 experimental

Base: `yc_1.15.4_ycsite.apk`, release `2.01` deste repositório.
Inicializador próprio em Java para a base TV, voltado a Android 9 e 10.
O carregador adicionado pelo mod de terceiros não é reutilizado.

## Correção implementada na v3.1

A coleta da v3 registra `SIGSEGV`, endereço `0x35f`, antes do retorno da
fábrica original. O RIP, combinado com os mapas, corresponde a
`libexec.so + 0x6c34d`: `cmp byte ptr [rax + 0x35f], 0`, com `rax = 0`.
Esse offset é relativo à base ELF; o `0x3834d` do tombstone é relativo ao
mapeamento anônimo do código descompactado.

A leitura estática identifica, na chamada anterior, uma rotina que abre a
imagem indicada, obtém o caminho pelo descritor e o compara com o caminho
informado. Quando os textos diferem, ela zera a estrutura global. Os mapas
confirmam o caminho físico `/data/data` para a imagem privada. A v3 usava
`getAbsolutePath()`, que preserva aliases como `/data/user/0`. A coleta não
registrou os dois argumentos da comparação; a divergência é a hipótese de
causa tratada por esta versão, não uma confirmação em execução.

A v3.1 abre o arquivo validado e usa `Os.readlink("/proc/self/fd/" + fd)`
para definir o caminho fornecido ao carregador e aos adaptadores existentes.
O descritor é fechado em seguida. Isso evita depender da grafia do diretório
recebida de `ApplicationInfo.dataDir`. A mensagem de inicialização distingue
v3.1 e informa se houve normalização do caminho.

Esta revisão altera somente essa resolução de caminho e a identificação da
versão. Mantém o restante do comportamento da v3. Não altera o binário nativo.

## Preparação implementada na v3

A coleta executada pelo usuário confirmou chamadas `kill(0, 9)` no contexto
de threads com o nome do aplicativo, antes do encerramento observado pelo
ActivityManager. As quatro etapas Java da v2 se completam. O rastreamento não
registrou o endereço de usuário, apesar da opção de userstacktrace habilitada.
A condição exata que chega ao encerramento nativo ainda não foi identificada.

A v3 trata uma limitação concreta da v2: o adaptador Java apresentava o
certificado original, mas o carregador ainda recebia o arquivo recomposto.
Agora uma imagem integral, com a assinatura original, acompanha o contêiner.

1. Extrai a imagem para os dados privados e confere tamanho e SHA-256.
2. Nas aberturas seguintes, reutiliza a imagem depois de conferir seu hash.
3. Fornece esse caminho ao `ApplicationInfo` passado ao carregador original.
4. Adapta `sourceDir`, `publicSourceDir`, `mAppDir` e `mResDir` do processo.
5. Apresenta o mesmo caminho nas consultas locais de `ApplicationInfo` e
   `PackageInfo` referentes ao próprio pacote.
6. Mantém a identidade UUID privada e a aplica a `Build.FINGERPRINT` antes
   de delegar à fábrica original. Limpar os dados recria essa identidade.

A cópia original tem SHA-256:
`5629c0dc0dc0b631f09bd21f81a5d671e64e6d516cb4a28a9b9fb45a2971b231`.
O certificado público original utilizado pelo adaptador tem SHA-256:
`0fd3d98319e7dc05830accaedcc9e2af8f3b89234a21a4d4e5ff5e04fecbb2a7`.

A imagem é gravada por arquivo temporário, sincronizada e renomeada após a
conferência. A rotina não troca as bibliotecas nativas do original nem bloqueia
syscalls de encerramento. As mensagens `YCLean` indicam a preparação da imagem,
a delegação e o retorno da criação do aplicativo original.

## Tamanho e estado da entrega

O APK inclui a imagem assinada original de aproximadamente 34 MB além do
contêiner. Por isso a v3 fica próxima de 68 MB. O código novo continua sendo
Java, sem bibliotecas nativas próprias. Os dados extraídos são apagados pela
limpeza dos dados do aplicativo.

Compilação e publicação pelo workflow; testes de execução e validação nos
dispositivos ficam com o usuário, conforme sua solicitação. A v3 sofreu crash
na coleta enviada. Não foi confirmado que a v3.1 elimine a falha ou renove
o trial; a revisão corrige a resolução do caminho fornecido ao carregador.

O certificado realmente registrado pelo Android continua sendo o da nova
assinatura de desenvolvimento. Não há virtualização completa das verificações
nativas do sistema. O carregador protegido e o player ARM originais permanecem.
O MEmu utiliza sua ponte ARM; a presença dela não prova a compatibilidade de
cada biblioteca. A geração local de outra identidade não garante novo trial
no servidor.

## Compilar

Linux, Python 3.11+ e JDK 17 ou 21:

```sh
python3 build.py
```

Saída: `build/yc-tv-1.15.4-lean-v3.1.apk`. O script baixa as ferramentas e o APK
base, confere os hashes dos insumos, compila, empacota e assina. Não executa
o aplicativo nem testes. A verificação do assinador faz parte da geração.

O workflow `YC TV Lean Build` publica APK e fontes na release
`yc-tv-1.15.4-lean-v3.1`.
