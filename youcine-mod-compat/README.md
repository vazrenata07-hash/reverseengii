# Mod original: correção nativa de inicialização v2

Entrada: YOUCINE.TV.MOD.apk da release 2.0, SHA256
`cf725dbfa652671f925a517ab9e42e8bafcbff8fdc6e0b600d573c3e87a8f51e`.

O tombstone fornecido registra SIGSEGV/SEGV_ACCERR no Houdini x86, offset
0x291084. A instrução rep movsd copia 8 bytes para 0x0b842e38, dentro do
mapeamento somente de leitura de /system/lib/arm/nb/libc.so. A origem da
cópia contém um salto ARM para a biblioteca original do carregador.

## Mudança

O módulo em res/dex/classes.dex, o APK em res/origin.apk e todas as
bibliotecas de player e proteção sob lib/ permanecem idênticos à entrada.
Os hooks do módulo não são desativados ou reescritos.

As duas bibliotecas @monxx_mod/arm.so e arm64.so mantêm tamanho, código de
máquina e endereços originais. Apenas os imports mprotect/memcpy são
redirecionados para um auxiliar ARM pequeno, carregado previamente.
O slot redundante DT_FLAGS=BIND_NOW passa a referenciar a dependência
yc_mprot; DT_FLAGS_1=NOW é mantido. As versões dos dois imports passam
para GLOBAL sem alterar os demais símbolos ou relocações.

Em processos traduzidos, o auxiliar ARM usa JNI para chamar o auxiliar
x86/x86_64 correspondente ao processo real. Esse auxiliar executa mprotect
na Bionic real do Android, fora do syscall ARM traduzido. A cópia observada
no tombstone recebe uma verificação adicional: páginas de código ARM
somente de leitura ganham escrita temporária, seguida da restauração da
proteção e limpeza do cache de instruções. Falhas geram mensagens
YCModCompat com errno, sem fingir que a instalação teve sucesso.

Em ARM nativo, os auxiliares delegam às funções originais da libc.
A publicação do backup Java e os atributos multiArch/use32bitAbi da v1
permanecem. A classe auxiliar é incorporada ao DEX principal; não há DEX
extra nem diretórios x86 em lib/ que alterem a seleção das bibliotecas do app.
As bibliotecas extraídas são comparadas com o conteúdo do APK para impedir
que lib.so de uma instalação anterior seja reutilizada por ter o mesmo tamanho.

## Compilar

Java 21, Python 3.10+, pyelftools 0.33 e Android NDK r26d:

```sh
python3 -m pip install pyelftools==0.33
export ANDROID_NDK_HOME=/caminho/android-ndk-r26d
python3 build.py --work build --out dist
```

A compilação gera quatro auxiliares: duas pontes ARM e dois executores
x86. Dependências Java e APK têm SHA256 fixados. CHANGESET.json registra
as quatro entradas alteradas, as quatro adicionadas e hashes preservados.
O empacotamento é interrompido se outro conteúdo do APK original mudar.

A entrega corrige a operação de escrita registrada. Outros comportamentos
do motor nativo original sob tradução podem exigir ajustes distintos.
Compilação e integridade do pacote são verificadas. Não são executados
APK, emulador, testes de trial ou testes no aparelho; essa execução fica
com o usuário. A eliminação do crash ainda depende do teste no dispositivo.

O pacote continua com.world.youcinetv e usa a mesma assinatura de desenvolvimento
da compat-v1, permitindo atualização sobre ela. Para substituir uma versão
assinada por terceiros, pode ser necessária a desinstalação da anterior.
