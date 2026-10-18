# Mint Portable V24 — danill0

Correção de compatibilidade da V23. Windows 10/11 x64; .NET incluído. Requer Microsoft Edge WebView2 Runtime.

## Alteração

A V23 criava `window.jsBridge` em `888pg.cc` antes dos scripts do site. Esse nome é usado na detecção de aplicativo Android descrita na captura original. A ponte portada fornece somente adblock, portanto sua presença pode direcionar a inicialização do lobby para uma integração de aplicativo incompleta.

A V24 usa `window.__mintAdblockBridge` para a comunicação interna do filtro. Deixa de criar `window.jsBridge` e preserva uma ponte que o próprio site possa publicar. Os seis métodos nativos de adblock continuam funcionando.

O diff do JavaScript funcional da V23 para V24 contém apenas a troca desse nome. Cadastro, senha danill0, PIN, filtro, histórico, contador, user agent Android e largura da janela continuam com o mesmo código. O gerador agora usa o arquivo Android rastreado em `src-v21`, permitindo regenerar o script a partir do repositório.

## Usar

Feche o Mint anterior e execute `Mint-Browser-Windows-v24-Portable-danill0.exe` na mesma pasta. Pode continuar usando `MintData` da V22/V23; a atualização não exige limpar os dados.

## Verificação e limite

Compilação Release Windows x64 concluída. Passaram sete verificações focadas em JavaScript: ausência do marcador de aplicativo da V23, preservação de uma ponte do site, encaminhamento dos seis métodos nativos, limites de domínio/frame, ausência de COM/WebView, comparação exata do script gerado e ida/volta das mensagens do contador em simulação.

Não houve execução no Windows nem acesso funcional ao site neste ambiente. Sem a mensagem original do Console, a chamada exata que causou o travamento permanece não confirmada; a V24 remove a interferência isolada na comparação V22/V23.

SHA-256 do EXE: `40ac209ebdac67df708cee5efddac076b5d9f8df21c082740cbf20c4136771c4`.
