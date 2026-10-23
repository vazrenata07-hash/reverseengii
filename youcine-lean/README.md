# YC TV 1.15.4 — inicializador Java próprio, v1 experimental

Base: `yc_1.15.4_ycsite.apk`, release `2.01` deste repositório.

O inicializador novo contém duas classes Java e não contém bibliotecas nativas
próprias. A referência técnica é a geração de `fingerprint` com
`UUID.randomUUID()` nos construtores das classes `PreInstallAuthBean` e
`SnTokenBean` do mod TV 1.15.1 fornecido para análise. O código dessas classes
e do carregador do mod não foi reutilizado.

## Comportamento implementado

- Cria uma identidade UUID v4 nos dados privados do aplicativo.
- Conserva essa identidade nas aberturas seguintes.
- Limpar todos os dados do aplicativo remove essa identidade; a próxima
  inicialização cria outra. Limpar apenas o cache não a remove.
- Aplica a identidade a `Build.FINGERPRINT` somente no processo do aplicativo,
  antes de `Application.onCreate`, por um `ContentProvider` privado.
- Se a rotina falhar, registra a falha e permite a inicialização original.

Persistência com bloqueio de arquivo sem espera, escrita temporária, sincronização
e renomeação. Sem rede, permissões extras, tela adicional ou serviços próprios.
O empacotamento adiciona o provider e um DEX ao APK original, preservando o
conteúdo dos outros arquivos e recompilando somente o código novo.

## Estado da entrega

Protótipo compilado, não executado. Por solicitação do usuário, não foram
executados testes de abertura, de trial ou de compatibilidade.

A atribuição em `Build.FINGERPRINT` é uma estratégia nova de integração. Não foi
confirmado que os construtores protegidos da versão 1.15.4 consultem esse campo
nesse ponto, nem que o servidor conceda outro trial. Não é uma reprodução
comprovada de todo o comportamento do mod.

O carregador protegido Ijiami original continua presente e executa antes do
provider. Esta implementação não corrige falhas anteriores à criação do
provider e não contorna verificações da assinatura original. O APK gerado usa
uma assinatura de desenvolvimento diferente da assinatura do original; não
pode ser instalado como atualização dele.

O código novo é Java e não depende de ARM ou x86. As bibliotecas originais do
player continuam sendo ARM de 32 e 64 bits; um emulador x86_64 precisa de
tradução ARM compatível. Não foi acrescentado um player x86_64.

## Compilar

Linux, Python 3.11+ e JDK 17 ou 21:

```sh
python3 build.py
```

Saída: `build/yc-tv-1.15.4-lean-v1.apk`. O script baixa as ferramentas e o APK
base, confere os hashes dos insumos, compila o código, empacota e assina. Não
abre o aplicativo e não executa testes. A checagem feita pelo assinador faz
parte da geração do APK.

O workflow `YC TV Lean Build` publica APK e fontes na release
`yc-tv-1.15.4-lean-v1`.
