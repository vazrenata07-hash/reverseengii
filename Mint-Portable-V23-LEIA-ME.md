# Mint Portable V23 — danill0

Windows 10/11 x64. Execute em uma pasta com permissão de escrita. O .NET está incluído; Microsoft Edge WebView2 Runtime precisa estar instalado. O aplicativo mantém perfil, cache, configurações, contador e histórico em MintData junto ao EXE. Pode continuar usando MintData da V22. A interface acompanha a largura real da janela.

## Integração nativa portada

O APK Mint fornece window.jsBridge usando AdblockWebView$d, com seis métodos públicos: getAddDomListener, getElemhideSelectors, isElementsHidden, setAddDomListener, setElementsHidden e setHideElementCount.

A V23 fornece os mesmos seis métodos com implementação nativa C# acessível pelo host WebView2. O filtro informa a quantidade de camadas ocultas e seu estado à ponte. Os seletores retornados correspondem ao filtro existente. A interface só é publicada no contexto principal de 888pg.cc e subdomínios; os métodos nativos verificam esse contexto. Não expõe arquivos, navegação, credenciais ou reflexão ao site.

## Evidência e limite

O HTML do site presente na captura define LOBBY_UTILS.isAppEnv consultando, entre outros sinais, window.jsBridge. Também define isVestEnv como isAppEnv sem SpeedPackage. O APK tem essa ponte e as versões Windows V21/V22 não a tinham. Isso fornece uma diferença concreta para a integração.

Esse código capturado usa a classificação na adaptação do viewport. O bundle principal do lobby, responsável pela montagem dos metadados de login, não está na captura. Portanto a presença da integração nativa não comprova antecipadamente o registro APP-Android(Vest) no servidor. A V23 não modifica o texto da tela de dispositivos, não força valores de cabeçalhos de cliente e não altera metadados ou assinaturas de login.

A classificação precisa ser observada em um login novo: o site pode conservar os metadados da sessão existente. O código e as funções de cadastro, PIN, filtro, contador e histórico foram preservados; apenas acrescentada a ponte de adblock ausente. A identificação de navegador continua Android Browser 4.0, Samsung SM-A536B, Android 13, como na V22. O motor continua WebView2 no Windows.

Compilação Windows x64 concluída. Não foram executados testes funcionais no Windows/site nem baterias de regressão, conforme preferência do usuário. O executável não tem assinatura comercial de código Windows.
