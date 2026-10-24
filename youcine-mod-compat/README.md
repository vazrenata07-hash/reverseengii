# Correção do carregador do mod original

Entrada: `YOUCINE.TV.MOD.apk` da release `2.0`, SHA256
`cf725dbfa652671f925a517ab9e42e8bafcbff8fdc6e0b600d573c3e87a8f51e`.

Este patch altera somente `classes.dex` externo e `AndroidManifest.xml`.
O módulo em `res/dex/classes.dex`, o APK original embutido em `res/origin.apk`,
os outros DEX e todas as bibliotecas nativas permanecem idênticos à entrada.
A assinatura do APK externo é substituída para permitir distribuir o pacote alterado.

## Mudanças

- O campo do backup Java do Pine passa a ser `volatile`.
- A chamada ao método original aguarda a publicação desse backup antes de
  repassá-lo ao código nativo. O limite é 5 segundos; se a publicação falhar,
  uma exceção identificável substitui a desreferência de um ponteiro nulo.
- `multiArch=true` e `use32bitAbi=true` solicitam um processo de 32 bits
  quando suportado. O carregador fornecido contém pontes ARM32, ARM64 e x86,
  mas não uma ponte x86_64. As bibliotecas ARM64 continuam no pacote.

O código do módulo não foi refeito nem substituído. Sua rotina não foi
executada nesta entrega. Não há confirmação de que todo crash do APK de
terceiros tenha a mesma causa dos crashes anteriores do projeto Lean.
São correções de compatibilidade baseadas no carregador disponível.

## Compilar

Requisitos: Java 21 e Python 3.10 ou superior.

```sh
python3 build.py --work build --out dist
```

As dependências e o APK de entrada têm SHA256 fixados no script.
`CHANGESET.json` registra as duas entradas alteradas e os hashes dos
componentes preservados. O empacotamento falha se outro conteúdo mudar.
Não são executados testes de instalação, inicialização ou funcionamento;
esses testes ficam com o usuário.

O pacote mantém `com.world.youcinetv`. A assinatura diferente pode exigir
desinstalar a versão instalada antes de instalar esta versão.
