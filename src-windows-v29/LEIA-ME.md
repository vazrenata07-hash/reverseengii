# Mint V29

[Instruções do launcher](../Mint-Launcher-V29-LEIA-ME.md).

O mesmo EXE abre o launcher por padrão. O launcher inicia janelas com `--instance` e um identificador persistente validado. Cada perfil usa pasta de dados WebView2 e mutex próprios. A instância principal mantém o caminho legado `MintData`; as demais usam `MintInstances/<id>`. Não há compartilhamento de cookies, cache ou armazenamento de sites entre essas pastas.

Preferências globais ficam fora das pastas de sessão; a limpeza valida e bloqueia somente a instância escolhida, aguarda a saída do seu processo e motor WebView2 antes da exclusão. Proxy continua em `MintProxy.json`; um observador de arquivo sincroniza mudanças de configuração nas janelas abertas, sem reload. Alteração inválida de proxy habilitado bloqueia novas conexões até correção ou desativação explícita.

As otimizações são locais: reutilização de buffers de cabeçalhos de rede e remoção de leituras duplicadas na classificação de inputs. Não houve alterações de identificação do navegador, versões Android ou regras de validação dos sites.

Compilação apenas, sem testes ou benchmarks nesta entrega.
