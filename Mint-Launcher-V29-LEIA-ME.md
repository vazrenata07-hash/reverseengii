# Mint Launcher V29

Feche a versão anterior e coloque o EXE na mesma pasta da V28, com `MintData` e `MintProxy.json`. Ao abrir, aparece o launcher.

- **Principal (dados existentes)** usa a sessão já existente da V28.
- **Criar e abrir** cria uma instância com nome e cookies, cache, armazenamento e dados de sessão separados. Ela permanece na lista para as próximas aberturas.
- **Abrir instância** reabre o mesmo perfil. É possível manter várias instâncias abertas.
- Fechar o launcher mantém as instâncias abertas; ele pode ser reaberto pelo EXE.

O navegador continua com os recursos da V28 e a identificação real do Windows. O painel de dispositivos da V27 não está incluído.

## Configuração e limpeza

Proxy e preferências são compartilhados entre as instâncias. O proxy permanece em `MintProxy.json`, com senha protegida pelo usuário atual do Windows. Preferências e lista de instâncias ficam em `MintSettings`.

**Limpar dados e reiniciar** afeta somente os dados da instância atual. Mantém o nome da instância, o proxy e as preferências compartilhadas, e não apaga outras sessões. Dados das novas instâncias ficam em `MintInstances`; a principal continua em `MintData`.

Para mover tudo para outra pasta, leve o EXE e essas pastas/arquivos juntos. Em outro computador ou usuário do Windows, pode ser necessário informar novamente a senha do proxy.

## Proxy sem refresh

Ativar, desativar ou salvar um proxy ativo não chama reload nem reinicia o navegador. As conexões antigas são encerradas para que novas requisições usem a rota selecionada. O conteúdo já carregado permanece na página; pedidos em andamento podem falhar ou ser repetidos pelo próprio site, e WebSockets podem precisar se reconectar.

A mudança é sincronizada automaticamente nas instâncias abertas. O programa não repete ações anteriores nem pede uma nova página para validar a conexão. A rotação de IP continua a cargo do provedor. Um proxy ativo que falhar não retorna automaticamente à conexão direta.

## Otimização

Esta versão reduz leituras redundantes do DOM ao classificar campos e reutiliza buffers temporários no adaptador de proxy, reduzindo alocações transitórias. O adaptador permanece disponível para permitir trocar o proxy sem refresh. Não houve medição que confirme a causa ou a eliminação do stutter.

Cada instância tem seus próprios processos de navegação e consumo de memória; abrir várias aumenta o uso de recursos. Nenhum teste ou benchmark foi executado, conforme solicitado. A entrega foi compilada para Windows x64, com .NET incluído; continua exigindo WebView2 Runtime.
