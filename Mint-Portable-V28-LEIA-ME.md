# Mint Portable V28 — proxy

Baseado na V26, com os botões **Config. proxy** e **Proxy: ligado/desligado**. O painel de dispositivos da V27 não faz parte desta versão.

1. Feche a versão anterior e abra o EXE na mesma pasta.
2. Clique em **Config. proxy**, escolha HTTP, HTTPS ou SOCKS5 e informe endereço, porta e, se necessário, usuário e senha. Salve.
3. Use **Proxy: desligado** para ativar. O botão passa a **Proxy: ligado**. Clique novamente para voltar à conexão direta.

Ativar, desativar ou editar um proxy ativo encerra as conexões anteriores e recarrega as abas; conclua formulários antes de mudar a conexão. Todas as abas compartilham a configuração.

A rotação de IP é controlada pelo provedor. O navegador usa o endereço configurado, sem serviço próprio de rotação.

A configuração é salva em `MintProxy.json`, ao lado do EXE. A senha usa a proteção de dados do usuário atual do Windows (DPAPI). Ao mover para outro usuário/computador, pode ser necessário informá-la novamente. **Limpar dados** mantém essa configuração de rede e limpa o `MintData` conforme a V26.

HTTP/HTTPS indicam a conexão até o servidor proxy; ambos atendem navegação HTTP e HTTPS. SOCKS5 aceita autenticação de usuário/senha. Se o proxy ativo falhar, a requisição falha; não há retorno automático à conexão direta. A ponte nativa e o perfil Windows da V26 foram preservados.

O proxy atende conexões HTTP(S) e WebSocket do navegador. Não configura a rede de outros aplicativos nem um túnel VPN/UDP.

Compilado para Windows x64 com .NET incluído; requer WebView2 Runtime. Nenhum teste foi executado, conforme solicitado pelo usuário.
