# Mint Windows V28

Consulte [as instruções da V28](../Mint-Portable-V28-LEIA-ME.md).

Esta fonte parte da V26 e acrescenta um painel convencional de configuração HTTP/HTTPS/SOCKS5 e uma chave manual de ativação. Não altera a identificação do navegador nem o código do fluxo de cadastro.

Um adaptador HTTP local, restrito ao loopback e autenticado com um segredo criado por processo, permite usar os três protocolos com autenticação de usuário/senha. Quando desligado, ele usa conexão direta; quando ligado, só usa o endpoint configurado. Credenciais da conexão local não são encaminhadas ao destino; credenciais do provedor são usadas somente na autenticação com o proxy. O adaptador não descriptografa os túneis TLS dos sites e não registra requisições, respostas ou credenciais.

As preferências são salvas separadamente em `MintProxy.json`, com senha protegida por DPAPI CurrentUser. A limpeza de `MintData` não exclui as preferências de rede. Configuração habilitada ilegível ou inválida impede a abertura da navegação até configurar novamente ou desativar explicitamente.

A alteração foi compilada; a operação no Windows e com o provedor será testada pelo usuário. Não foram criados nem executados testes nesta entrega.
